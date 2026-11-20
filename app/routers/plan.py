"""空闲段 + 周计划接口（docs/API.md §3⑤ / ⑥ / ⑦）。

    GET  /api/slots?date=2026-11-19     查某天的空闲段
    POST /api/plan/generate             生成/覆盖某一周的计划
    GET  /api/plan/{week_start}         查某一周已生成的计划

算法都在 `app/services/slots.py`（空闲段）和 `app/services/scheduler.py`（排任务）里，
这个文件只做：校验参数 → 查库 → 调纯函数 → 写库 → 拼冻结好的 JSON。
"""

import re
from datetime import date as date_cls
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, SQLModel, select

from app.db import get_session
from app.models import Block, Course, FixedEvent, Plan, Task
from app.services.scheduler import build_plan
from app.services.slots import WINDOW_END, WINDOW_START, free_segments, to_hhmm

router = APIRouter(tags=["空闲段 / 计划"])

TERM = "2026f"
# 只认 2026-11-19 这种格式
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class GenerateIn(SQLModel):
    """POST /api/plan/generate 的请求体。"""

    week_start: str


# ---------------------------------------------------------------- 小工具

def _parse_date(value: str) -> date_cls:
    """把 "2026-11-16" 转成日期；格式不对直接 422（中文 detail）。"""
    if not isinstance(value, str) or DATE_PATTERN.match(value) is None:
        raise HTTPException(status_code=422, detail="日期要写成 2026-11-19 这样的格式")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="日期要写成 2026-11-19 这样的格式")


def _title_maps(
    courses: list[Course], events: list[FixedEvent], tasks: list[Task]
) -> tuple[dict, dict, dict]:
    """给 GET 用：block 表没存 title，按"星期+起止分钟"反查名字。"""
    course_titles = {(c.weekday, c.start_min, c.end_min): c.name for c in courses}
    fixed_titles = {(e.weekday, e.start_min, e.end_min): e.name for e in events}
    task_titles = {t.id: t.title for t in tasks}
    return course_titles, fixed_titles, task_titles


def _block_to_json(
    row: Block, course_titles: dict, fixed_titles: dict, task_titles: dict
) -> dict:
    """把 block 表的一行转成接口格式（时间变回 "HH:mm"）。"""
    weekday = date_cls.fromisoformat(row.date).isoweekday()
    key = (weekday, row.start_min, row.end_min)

    if row.kind == "task":
        title = task_titles.get(row.task_id, "任务")
    elif row.kind == "course":
        title = course_titles.get(key, "课程")
    else:
        title = fixed_titles.get(key, "固定事件")

    return {
        "id": row.id,
        "date": row.date,
        "start": to_hhmm(row.start_min),
        "end": to_hhmm(row.end_min),
        "kind": row.kind,
        "task_id": row.task_id,
        "title": title,
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
    blocks_json = [
        _block_to_json(row, course_titles, fixed_titles, task_titles) for row in rows
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
    blocks_json = [
        _block_to_json(row, course_titles, fixed_titles, task_titles) for row in rows
    ]

    scheduled_ids = {row.task_id for row in rows if row.kind == "task"}
    unscheduled = [
        {
            "task_id": task.id,
            "title": task.title,
            "reason": "这一周没有排进去（重新生成一次看具体原因）",
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
