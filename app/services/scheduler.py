"""排程算法：空闲段 + 任务 → 时间块（纯函数，不 import FastAPI、不碰数据库）。

规则来自 `docs/API.md` §3⑥（v0.5 冻结）和 11-20 任务卡 §2：

1. 把这一周 7 天各算一次空闲段（复用 `services/slots.py` 的 `free_segments`）；
2. 候选排序：**晚自习（evening）> 周末整天 > 工作日白天空档**，同档按日期、开始时间取最早；
3. 任务排序：`priority` 小的先（1 最高），同优先级 `deadline` 早的先；
4. 放：整段放得下就整段放；放不下才切，每块 **45–120 分钟**，最后一块可以短一点但 **≥15 分钟**；
5. 任务块**不跨 19:00 / 21:00**（`free_segments` 已经切好了，这里不再拼回去）；
6. 排不下 → 进 `unscheduled`，`reason` 必须是人能看懂的一句话。

输出只有任务块（kind="task"）；课和固定事件由 `routers/plan.py` 补进 blocks。
同样的输入必须输出同样的结果——**这里没有随机数**。
"""

from dataclasses import dataclass
from datetime import date as date_cls
from datetime import timedelta

from app.services.slots import free_segments

# 15 分钟网格的起点：07:30
GRID_START = 450
GRID = 15

# 单个任务块的上限 / 下限
MAX_BLOCK = 120
MIN_BLOCK = 15
MIN_SPLIT_BLOCK = 45


@dataclass
class _Slot:
    """一个可用的空闲段。"""

    date: str
    weekday: int
    start: int
    end: int
    kind: str  # "free" / "evening"


def _tier(slot: _Slot) -> int:
    """候选优先级：晚自习 0，周末 1，工作日白天 2（数字越小越先放）。"""
    if slot.kind == "evening":
        return 0
    if slot.weekday >= 6:
        return 1
    return 2


def _align(minute: int) -> int:
    """把起点对齐到 15 分钟网格（450 + 15k），往后取整。"""
    if minute <= GRID_START:
        return GRID_START
    offset = minute - GRID_START
    return GRID_START + ((offset + GRID - 1) // GRID) * GRID


def _week_slots(week_start: str, courses: list[dict], fixed_events: list[dict]) -> list[_Slot]:
    """生成这一周 7 天的所有空闲段，并按"晚自习 > 周末 > 工作日"排好。"""
    first_day = date_cls.fromisoformat(week_start)
    slots: list[_Slot] = []

    for offset in range(7):
        day = first_day + timedelta(days=offset)
        weekday = day.isoweekday()  # 1=周一 … 7=周日
        busy: list[tuple[int, int]] = [
            (course["start_min"], course["end_min"])
            for course in courses
            if course["weekday"] == weekday
        ]
        busy += [
            (event["start_min"], event["end_min"])
            for event in fixed_events
            if event["weekday"] == weekday
        ]
        for start, end, kind in free_segments(busy, weekday):
            slots.append(_Slot(day.isoformat(), weekday, start, end, kind))

    slots.sort(key=lambda slot: (_tier(slot), slot.date, slot.start))
    return slots


def _make_block(slot: _Slot, start: int, minutes: int, task: dict) -> dict:
    return {
        "date": slot.date,
        "start_min": start,
        "end_min": start + minutes,
        "kind": "task",
        "task_id": task.get("id"),
        "title": task["title"],
    }


def _reason_no_room(task: dict, eligible: list[_Slot], placed: int, remaining: int) -> str:
    """排不下时给一句人话原因。"""
    deadline = (task.get("deadline") or "")[:10]
    if not eligible:
        if deadline:
            return f"截止时间已过（{deadline}），这一周排不进去"
        return "这一周没有可用的空档"

    longest = max(slot.end - _align(slot.start) for slot in eligible)
    if placed == 0:
        return f"这一周的空档最长只有 {longest} 分钟，任务需要 {remaining} 分钟"
    return f"还剩 {remaining} 分钟，找不到能放下 45–120 分钟的连续空档"


def build_plan(
    week_start: str,
    courses: list[dict],
    fixed_events: list[dict],
    tasks: list[dict],
) -> tuple[list[dict], list[dict]]:
    """生成这一周的任务块。

    参数：
        week_start    -- 那一周的周一，"2026-11-16"
        courses       -- [{"name","weekday","start_min","end_min"}, ...]
        fixed_events  -- [{"name","weekday","start_min","end_min"}, ...]
        tasks         -- [{"id","title","duration_min","deadline","priority"}, ...]

    返回：
        (task_blocks, unscheduled)
        task_blocks 里每项：date / start_min / end_min / kind="task" / task_id / title
        unscheduled 里每项：task_id / title / reason
    """
    slots = _week_slots(week_start, courses, fixed_events)
    week_first = date_cls.fromisoformat(week_start)

    ordered_tasks = sorted(
        tasks,
        key=lambda task: (
            int(task.get("priority", 2)),
            task.get("deadline") or "9999-12-31T23:59:59",
            task.get("id") or 0,
        ),
    )

    blocks: list[dict] = []
    unscheduled: list[dict] = []

    for task in ordered_tasks:
        title = task.get("title") or "未命名任务"
        duration = int(task.get("duration_min") or 0)
        task_id = task.get("id")

        # 时长本身就不合法：小于 15 分钟排不进任何块
        if duration < MIN_BLOCK:
            unscheduled.append(
                {"task_id": task_id, "title": title, "reason": "任务时长不足 15 分钟，排不进任何时间块"}
            )
            continue

        deadline = (task.get("deadline") or "")[:10]
        if deadline and date_cls.fromisoformat(deadline) < week_first:
            unscheduled.append(
                {"task_id": task_id, "title": title, "reason": f"截止时间已过（{deadline}），这一周排不进去"}
            )
            continue

        eligible = [slot for slot in slots if not deadline or slot.date <= deadline]

        remaining = duration
        placed_minutes = 0
        task_blocks: list[dict] = []

        # 第一遍：整段放得下就整段放（单个任务块最多 120 分钟）
        if remaining <= MAX_BLOCK:
            for slot in eligible:
                start = _align(slot.start)
                if start + remaining <= slot.end:
                    task_blocks.append(_make_block(slot, start, remaining, task))
                    slots.remove(slot)
                    placed_minutes += remaining
                    remaining = 0
                    break

        # 第二遍：整段放不下，才切成 45–120 分钟的块
        for slot in list(slots):
            if remaining <= 0:
                break
            if slot not in eligible:
                continue

            start = _align(slot.start)
            capacity = slot.end - start
            if capacity < MIN_BLOCK:
                continue

            if remaining <= capacity:
                chunk = remaining  # 最后一块，可以短一点，但 ≥15
            else:
                chunk = min(MAX_BLOCK, capacity)
                if remaining - chunk < MIN_BLOCK:
                    chunk = remaining - MIN_BLOCK  # 让最后一块至少 15 分钟
                if chunk < MIN_SPLIT_BLOCK:
                    continue

            task_blocks.append(_make_block(slot, start, chunk, task))
            slots.remove(slot)
            placed_minutes += chunk
            remaining -= chunk

        blocks.extend(task_blocks)

        if remaining > 0:
            unscheduled.append(
                {
                    "task_id": task_id,
                    "title": title,
                    "reason": _reason_no_room(task, eligible, placed_minutes, remaining),
                }
            )

    blocks.sort(key=lambda block: (block["date"], block["start_min"]))
    return blocks, unscheduled
