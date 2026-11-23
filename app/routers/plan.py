"""空闲段 + 周计划 + 打卡 / 统计 / 导出 接口（docs/API.md §3⑤–⑩）。

    GET   /api/slots?date=2026-11-19     查某天的空闲段
    POST  /api/plan/generate             生成/覆盖某一周的计划
    GET   /api/plan/{week_start}         查某一周已生成的计划
    PATCH /api/checkin                   打卡（同任务同天幂等）
    GET   /api/stats/week                这一周的统计（4 个指标 + 恒 7 条 by_day）
    GET   /api/export.md                 导出这一周的 Markdown 周报

算法都在 `app/services/slots.py`（空闲段）和 `app/services/scheduler.py`（排任务）里，
这个文件只做：校验参数 → 查库 → 调纯函数 → 写库 → 拼冻结好的 JSON。
"""

import re
from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from app.db import get_session
from app.models import Block, Checkin, Course, FixedEvent, Plan, Task
from app.services.scheduler import build_plan
from app.services.slots import WINDOW_END, WINDOW_START, free_segments, to_hhmm

router = APIRouter(tags=["空闲段 / 计划"])

TERM = "2026f"
# 只认 2026-11-19 这种格式
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# "没排下"的通用原因：生成接口会给更具体的原因，但原因没有存库，
# 所以 /api/stats/week 和 /api/export.md 只能给这句通用说明。
UNPLANNED_REASON = "这一周没有排进去（重新生成一次看具体原因）"

# 导出 Markdown 的星期名（周一=1 … 周日=7）
WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
# 时间区间用短横线 "–"（不是减号），导出结构是冻结的
TIME_DASH = "–"


class GenerateIn(SQLModel):
    """POST /api/plan/generate 的请求体。"""

    week_start: str


# ---------------------------------------------------------------- 小工具

def _parse_date(value: str, example: str = "2026-11-19") -> date_cls:
    """把 "2026-11-16" 转成日期；格式不对直接 422（中文 detail）。

    example 是提示里举的例子：不同接口合同里写的例子日期不一样
    （/api/checkin 写的是 2026-11-23），detail 要能原样给用户看。
    """
    message = f"日期要写成 {example} 这样的格式"
    if not isinstance(value, str) or DATE_PATTERN.match(value) is None:
        raise HTTPException(status_code=422, detail=message)
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail=message)


def _title_maps(
    courses: list[Course], events: list[FixedEvent], tasks: list[Task]
) -> tuple[dict, dict, dict]:
    """给 GET 用：block 表没存 title，按"星期+起止分钟"反查名字。"""
    course_titles = {(c.weekday, c.start_min, c.end_min): c.name for c in courses}
    fixed_titles = {(e.weekday, e.start_min, e.end_min): e.name for e in events}
    task_titles = {t.id: t.title for t in tasks}
    return course_titles, fixed_titles, task_titles


def _block_to_json(
    row: Block,
    course_titles: dict,
    fixed_titles: dict,
    task_titles: dict,
    checked_keys: set[tuple[int, str]] | None = None,
) -> dict:
    """把 block 表的一行转成接口格式（时间变回 "HH:mm"）。

    checked_keys 是已打卡的 (task_id, date) 集合：只有 task 块且命中时才 done=True，
    其余（course / fixed，以及还没打卡的 task）一律 done=False。
    """
    weekday = date_cls.fromisoformat(row.date).isoweekday()
    key = (weekday, row.start_min, row.end_min)

    if row.kind == "task":
        title = task_titles.get(row.task_id, "任务")
    elif row.kind == "course":
        title = course_titles.get(key, "课程")
    else:
        title = fixed_titles.get(key, "固定事件")

    done = (
        row.kind == "task"
        and row.task_id is not None
        and checked_keys is not None
        and (row.task_id, row.date) in checked_keys
    )

    return {
        "id": row.id,
        "date": row.date,
        "start": to_hhmm(row.start_min),
        "end": to_hhmm(row.end_min),
        "kind": row.kind,
        "task_id": row.task_id,
        "title": title,
        "done": done,
    }


def _load_week_blocks(session: Session, plan_id: int) -> list[Block]:
    """取一份计划的所有块，按 date、start 升序。"""
    return session.exec(
        select(Block)
        .where(Block.plan_id == plan_id)
        .order_by(Block.date, Block.start_min)
    ).all()


# ---------------------------------------------------------------- 空闲段（D3）

@router.get("/api/slots")
def get_slots(
    date: str = Query(description="要查的日期，格式 2026-11-19"),
    session: Session = Depends(get_session),
) -> dict:
    """查某一天的空闲段（返回格式见 docs/API.md §3⑤）。"""
    parsed = _parse_date(date)
    weekday = parsed.isoweekday()  # 周一=1 … 周日=7

    courses = session.exec(
        select(Course).where(Course.weekday == weekday, Course.term == TERM)
    ).all()
    events = session.exec(
        select(FixedEvent).where(FixedEvent.weekday == weekday)
    ).all()

    busy = [(course.start_min, course.end_min) for course in courses]
    busy += [(event.start_min, event.end_min) for event in events]

    segments = free_segments(busy, weekday)
    items = [
        {
            "start": to_hhmm(start),
            "end": to_hhmm(end),
            "minutes": end - start,
            "kind": kind,
        }
        for start, end, kind in segments
    ]
    return {"date": date, "weekday": weekday, "items": items, "total": len(items)}


# ---------------------------------------------------------------- 生成计划（D6）

@router.post("/api/plan/generate", status_code=201)
def generate_plan(
    payload: GenerateIn,
    session: Session = Depends(get_session),
) -> dict:
    """生成某一周的计划；同一周再调一次会覆盖旧计划，不会叠加。"""
    week_start = payload.week_start
    week_first = _parse_date(week_start)

    courses = session.exec(select(Course).where(Course.term == TERM)).all()
    events = session.exec(select(FixedEvent)).all()
    tasks = [task for task in session.exec(select(Task)).all() if task.status != "done"]

    course_dicts = [
        {
            "name": course.name,
            "weekday": course.weekday,
            "start_min": course.start_min,
            "end_min": course.end_min,
        }
        for course in courses
    ]
    fixed_dicts = [
        {
            "name": event.name,
            "weekday": event.weekday,
            "start_min": event.start_min,
            "end_min": event.end_min,
        }
        for event in events
    ]
    task_dicts = [
        {
            "id": task.id,
            "title": task.title,
            "duration_min": task.duration_min,
            "deadline": task.deadline,
            "priority": task.priority,
        }
        for task in tasks
    ]

    task_blocks, unscheduled = build_plan(
        week_start, course_dicts, fixed_dicts, task_dicts
    )

    # 同一个 week_start 再生成：先删旧计划 + 旧块（覆盖，不叠加）
    old_plans = session.exec(select(Plan).where(Plan.week_start == week_start)).all()
    for old_plan in old_plans:
        for old_block in _load_week_blocks(session, old_plan.id):
            session.delete(old_block)
        session.delete(old_plan)
    session.commit()

    plan = Plan(
        week_start=week_start,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    # 课 + 固定事件 + 任务块，一起写进 block 表（合同：blocks 不含 free）
    rows_to_write: list[dict] = []
    for offset in range(7):
        day = week_first + timedelta(days=offset)
        weekday = day.isoweekday()
        for course in courses:
            if course.weekday == weekday:
                rows_to_write.append(
                    {
                        "date": day.isoformat(),
                        "start_min": course.start_min,
                        "end_min": course.end_min,
                        "kind": "course",
                        "task_id": None,
                    }
                )
        for event in events:
            if event.weekday != weekday:
                continue
            # 合同：所有 block 都必须在 07:30–21:30 之内；
            # 睡觉 00:00–07:30 / 23:00–24:00 这种窗外事件不写进 blocks。
            start_min = max(event.start_min, WINDOW_START)
            end_min = min(event.end_min, WINDOW_END)
            if end_min <= start_min:
                continue
            rows_to_write.append(
                {
                    "date": day.isoformat(),
                    "start_min": start_min,
                    "end_min": end_min,
                    "kind": "fixed",
                    "task_id": None,
                }
            )
    rows_to_write += task_blocks
    rows_to_write.sort(key=lambda row: (row["date"], row["start_min"]))

    for row in rows_to_write:
        session.add(
            Block(
                plan_id=plan.id,
                task_id=row.get("task_id"),
                date=row["date"],
                start_min=row["start_min"],
                end_min=row["end_min"],
                kind=row["kind"],
            )
        )
    session.commit()

    rows = _load_week_blocks(session, plan.id)
    course_titles, fixed_titles, task_titles = _title_maps(courses, events, tasks)
    checkins = session.exec(select(Checkin)).all()
    checked_keys = {(c.task_id, c.date) for c in checkins}
    blocks_json = [
        _block_to_json(row, course_titles, fixed_titles, task_titles, checked_keys)
        for row in rows
    ]
    scheduled_ids = {row.task_id for row in rows if row.kind == "task"}

    return {
        "plan_id": plan.id,
        "week_start": week_start,
        "blocks": blocks_json,
        "unscheduled": unscheduled,
        "stats": {
            "scheduled": len(scheduled_ids),
            "unscheduled": len(unscheduled),
        },
    }


# ---------------------------------------------------------------- 查计划（D6）

@router.get("/api/plan/{week_start}")
def get_plan(
    week_start: str,
    session: Session = Depends(get_session),
) -> dict:
    """查某一周已经生成的计划；没生成过 → 404。"""
    _parse_date(week_start)

    plan = session.exec(
        select(Plan).where(Plan.week_start == week_start).order_by(Plan.id.desc())
    ).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="这一周还没有计划")

    courses = session.exec(select(Course).where(Course.term == TERM)).all()
    events = session.exec(select(FixedEvent)).all()
    tasks = session.exec(select(Task)).all()

    rows = _load_week_blocks(session, plan.id)
    course_titles, fixed_titles, task_titles = _title_maps(courses, events, tasks)
    checkins = session.exec(select(Checkin)).all()
    checked_keys = {(c.task_id, c.date) for c in checkins}
    blocks_json = [
        _block_to_json(row, course_titles, fixed_titles, task_titles, checked_keys)
        for row in rows
    ]

    scheduled_ids = {row.task_id for row in rows if row.kind == "task"}
    unscheduled = [
        {
            "task_id": task.id,
            "title": task.title,
            "reason": UNPLANNED_REASON,
        }
        for task in tasks
        if task.status != "done" and task.id not in scheduled_ids
    ]

    return {
        "plan_id": plan.id,
        "week_start": week_start,
        "blocks": blocks_json,
        "unscheduled": unscheduled,
        "stats": {
            "scheduled": len(scheduled_ids),
            "unscheduled": len(unscheduled),
        },
    }


# ---------------------------------------------------------------- 打卡（D8）

class CheckinIn(SQLModel):
    """PATCH /api/checkin 的请求体（docs/API.md §3⑧）。

    date / task_id 故意收成 Any：docs/API.md §0 要求"出错一律返回
    {"detail": "中文说明"}，detail 能直接给用户看"。如果这里直接写 str / int，
    像 {"task_id": 1, "date": 20261123} 这种请求会先被 pydantic 拦住，
    detail 变成英文字段错误列表，前端就没法直接显示了。
    所以先原样收下，再在 check_in() 里用中文 422 说明哪里不对。
    """

    task_id: Any
    date: Any
    note: str | None = None


def _checkin_json(row: Checkin, created: bool) -> dict:
    """打卡记录的接口格式（字段名冻结：task_id/date/done_at/note/created）。"""
    return {
        "task_id": row.task_id,
        "date": row.date,
        "done_at": row.done_at,
        "note": row.note,
        "created": created,
    }


@router.patch("/api/checkin")
def check_in(payload: CheckinIn, session: Session = Depends(get_session)) -> dict:
    """打卡：同一天同一个任务重复打 → 仍然 200，但 created=false，不新增记录。

    幂等靠数据库的 (task_id, date) 唯一约束：直接插入，插入冲突就当成"已存在"。
    不要"先查再插"——并发时两边的查询都会说"没有"，然后都插入，500 就冒出来了。
    """
    parsed = _parse_date(payload.date, example="2026-11-23")

    if not isinstance(payload.task_id, int) or isinstance(payload.task_id, bool):
        raise HTTPException(status_code=422, detail="任务 id 必须是整数")

    task = session.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    row = Checkin(
        task_id=payload.task_id,
        date=parsed.isoformat(),
        done_at=datetime.now().isoformat(timespec="seconds"),
        note=payload.note,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # 唯一约束挡住重复打卡：回滚这次插入，把已经存在的那条原样返回
        session.rollback()
        existing = session.exec(
            select(Checkin).where(
                Checkin.task_id == payload.task_id,
                Checkin.date == parsed.isoformat(),
            )
        ).first()
        if existing is None:
            raise HTTPException(status_code=500, detail="打卡没保存成功，请再试一次")
        return _checkin_json(existing, created=False)

    session.refresh(row)
    return _checkin_json(row, created=True)


# ---------------------------------------------------------------- 周统计 / 导出（D8）

def _week_dates(week_start: str) -> list[str]:
    """week_start 起连续七天的 ISO 日期（by_day 永远 7 条、导出永远 7 个小节）。"""
    first = date_cls.fromisoformat(week_start)
    return [(first + timedelta(days=offset)).isoformat() for offset in range(7)]


def _require_plan(session: Session, week_start: str) -> Plan:
    """校验 week_start 格式（422），再取这一周最新的一份计划；没有就 404。"""
    _parse_date(week_start, example="2026-11-23")
    plan = session.exec(
        select(Plan).where(Plan.week_start == week_start).order_by(Plan.id.desc())
    ).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="这一周还没有计划")
    return plan


def _week_view(session: Session, plan: Plan, week_start: str) -> dict:
    """统计和导出共用的"一周全景"：块、任务、打卡、四个指标、按天/按类汇总。

    只读，不改库。返回值里带 `_` 前缀的中间数据只给导出用，不返回给接口。
    """
    days = _week_dates(week_start)
    week_end = days[-1]

    blocks = _load_week_blocks(session, plan.id)
    task_blocks = [row for row in blocks if row.kind == "task" and row.task_id is not None]
    tasks = session.exec(select(Task)).all()
    task_map = {task.id: task for task in tasks}

    scheduled_ids = {row.task_id for row in task_blocks}
    checkins = session.exec(
        select(Checkin)
        .where(Checkin.date >= week_start, Checkin.date <= week_end)
        .order_by(Checkin.date, Checkin.task_id)
    ).all()
    # 已完成的口径（totals 和 by_day 统一）：这一周里"被排进计划、并且打过卡"的任务数；
    # 同一个任务一周内打多次卡（不同日期）也只算 1 个。
    done_ids = {row.task_id for row in checkins if row.task_id in scheduled_ids}

    by_day = []
    for day in days:
        day_blocks = [row for row in task_blocks if row.date == day]
        by_day.append(
            {
                "date": day,
                "tasks": len(day_blocks),
                # done 记在"任务被安排的那一天"，不是"打卡操作发生的那一天"：
                # 报告里"周二安排了 2 个、完成 1 个"才读得通；
                # 这样 by_day 的 done 之和也等于 totals.done（任务被拆到两天时各算 1 次）。
                "done": len({row.task_id for row in day_blocks if row.task_id in done_ids}),
                "minutes": sum(row.end_min - row.start_min for row in day_blocks),
            }
        )

    category_rows: dict[str, dict] = {}
    for row in task_blocks:
        task = task_map.get(row.task_id)
        category = task.category if task is not None else "其他"
        item = category_rows.setdefault(
            category, {"tasks": set(), "done": set(), "minutes": 0}
        )
        item["tasks"].add(row.task_id)
        if row.task_id in done_ids:
            item["done"].add(row.task_id)
        item["minutes"] += row.end_min - row.start_min

    by_category = sorted(
        (
            {
                "category": category,
                "tasks": len(item["tasks"]),
                "done": len(item["done"]),
                "minutes": item["minutes"],
            }
            for category, item in category_rows.items()
        ),
        key=lambda row: (-row["minutes"], row["category"]),
    )

    unscheduled = [
        {"task_id": task.id, "title": task.title, "reason": UNPLANNED_REASON}
        for task in tasks
        if task.status != "done" and task.id not in scheduled_ids
    ]

    return {
        "week_start": week_start,
        "days": days,
        "task_blocks": task_blocks,
        "task_map": task_map,
        "checkins": checkins,
        "done_ids": done_ids,
        "totals": {
            "scheduled": len(scheduled_ids),
            "done": len(done_ids),
            "unscheduled": len(unscheduled),
            "planned_minutes": sum(row.end_min - row.start_min for row in task_blocks),
        },
        "by_day": by_day,
        "by_category": by_category,
        "unscheduled": unscheduled,
    }


@router.get("/api/stats/week")
def get_week_stats(
    week_start: str = Query(description="那一周的周一，格式 2026-11-23"),
    session: Session = Depends(get_session),
) -> dict:
    """这一周的统计（docs/API.md §3⑨）：4 个指标 + 恒 7 条 by_day + 按类汇总。"""
    plan = _require_plan(session, week_start)
    view = _week_view(session, plan, week_start)
    return {
        "week_start": week_start,
        "totals": view["totals"],
        "by_day": view["by_day"],
        "by_category": view["by_category"],
    }


def _export_markdown(view: dict) -> str:
    """把一周全景拼成冻结结构的 Markdown（docs/API.md §3⑩）。

    结构不许改：A 的「导出周报」按钮就是点这个链接，老师会直接打开看。
    """
    days = view["days"]
    totals = view["totals"]
    task_map = view["task_map"]
    done_ids = view["done_ids"]

    blocks_by_day: dict[str, list[Block]] = {}
    for row in view["task_blocks"]:
        blocks_by_day.setdefault(row.date, []).append(row)

    lines: list[str] = [
        f"# 课表排程周报 · {days[0]} ~ {days[-1]}",
        "",
        "## 概览",
        "",
        f"- 已排任务：{totals['scheduled']} 个 / {totals['planned_minutes']} 分钟",
        f"- 已完成：{totals['done']} 个",
        f"- 没排下：{totals['unscheduled']} 个",
        "",
        "## 每天安排",
        "",
    ]

    for day in days:
        parsed = date_cls.fromisoformat(day)
        label = WEEKDAY_NAMES[parsed.isoweekday() - 1]
        lines.append(f"### {label} {parsed.month:02d}-{parsed.day:02d}")

        day_blocks = sorted(blocks_by_day.get(day, []), key=lambda row: row.start_min)
        if not day_blocks:
            lines.append("- （没有安排）")
            continue
        for row in day_blocks:
            task = task_map.get(row.task_id)
            title = task.title if task is not None else "任务"
            mark = " ✅" if row.task_id in done_ids else ""
            start, end = to_hhmm(row.start_min), to_hhmm(row.end_min)
            lines.append(f"- {start}{TIME_DASH}{end} {title}{mark}")

    lines += ["", "## 没排下的任务", ""]
    if view["unscheduled"]:
        for item in view["unscheduled"]:
            lines.append(f"- {item['title']}：{item['reason']}")
    else:
        lines.append("- （没有）")

    lines += ["", "## 打卡记录", ""]
    if view["checkins"]:
        for row in view["checkins"]:
            task = task_map.get(row.task_id)
            title = task.title if task is not None else f"任务 {row.task_id}"
            lines.append(f"- {row.date} {title}")
    else:
        lines.append("- （还没有打卡）")

    return "\n".join(lines) + "\n"


@router.get("/api/export.md")
def export_markdown(
    week_start: str = Query(description="那一周的周一，格式 2026-11-23"),
    session: Session = Depends(get_session),
) -> Response:
    """导出这一周的 Markdown 周报（docs/API.md §3⑩）。

    必须用 Response + media_type 手动指定 UTF-8：用 PlainTextResponse 中文会乱码；
    加 Content-Disposition 浏览器才会"下载文件"而不是直接铺在页面上。
    """
    plan = _require_plan(session, week_start)
    view = _week_view(session, plan, week_start)
    markdown = _export_markdown(view)

    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="export-{week_start}.md"'},
    )
