"""空闲段计算（纯函数：不 import FastAPI、不碰数据库，方便单独测几百次）。

规则来自 `docs/API.md` §3⑤（v0.4 冻结）：

1. 一天只看 **07:30–21:30**（450–1290 分钟），绝不越界；
2. 扣掉当天的课、固定事件（传进来的是分钟区间，允许重叠、允许超出窗口）；
3. **周一到周五**在 18:50 / 19:00 / 21:00 / 21:10（1130/1140/1260/1270）四个点切开，
   **周六周日不切**（周末没有晚自习、没有通勤）；
4. 切完丢掉不足 **15 分钟**的碎片——两段 10 分钟的通勤（18:50–19:00、21:00–21:10）就此消失；
5. 完全落在 **19:00–21:00** 内的段，`kind` 标成 `"evening"`（晚自习，可以排任务），其余是 `"free"`。

输入输出都是普通整数/字符串，`app/routers/plan.py` 只负责查库和拼 JSON。
"""

# 一天可用窗口：07:30–21:30
WINDOW_START = 450
WINDOW_END = 1290

# 不足这个分钟数的碎片直接丢掉
MIN_MINUTES = 15

# 工作日要切开的四个点：18:50 / 19:00 / 21:00 / 21:10
CUTS = (1130, 1140, 1260, 1270)

# 晚自习：19:00–21:00
EVENING_START = 1140
EVENING_END = 1260


def to_hhmm(minutes: int) -> str:
    """把 480 转成 "08:00"。"""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """把重叠/相接的占用段合并，返回按开始时间排好的列表。"""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _subtract(
    busy: list[tuple[int, int]], start: int, end: int
) -> list[tuple[int, int]]:
    """从 [start, end) 里扣掉 busy（已合并），返回剩下的连续区间。"""
    free: list[tuple[int, int]] = []
    cursor = start

    for busy_start, busy_end in busy:
        # 只保留和窗口有交集的部分
        busy_start = max(busy_start, start)
        busy_end = min(busy_end, end)
        if busy_end <= busy_start:
            continue
        if busy_start > cursor:
            free.append((cursor, busy_start))
        cursor = max(cursor, busy_end)
        if cursor >= end:
            break

    if cursor < end:
        free.append((cursor, end))
    return free


def _split_at_cuts(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """在四个通勤/晚自习点上把区间切开（只对工作日调用）。"""
    pieces = list(intervals)
    for cut in CUTS:
        next_pieces: list[tuple[int, int]] = []
        for start, end in pieces:
            if start < cut < end:
                next_pieces.append((start, cut))
                next_pieces.append((cut, end))
            else:
                next_pieces.append((start, end))
        pieces = next_pieces
    return pieces


def free_segments(
    busy: list[tuple[int, int]], weekday: int
) -> list[tuple[int, int, str]]:
    """算某一天的空闲段。

    参数：
        busy    -- 当天所有占用 [(开始分钟, 结束分钟), ...]，课 + 固定事件都算
        weekday -- 1=周一 … 7=周日

    返回：
        [(开始分钟, 结束分钟, kind), ...]，按时间升序；kind 只有 "free" / "evening"。
    """
    merged = _merge([(start, end) for start, end in busy if end > start])
    segments = _subtract(merged, WINDOW_START, WINDOW_END)

    # 周末（6、7）不切：周末没有晚自习和通勤
    if 1 <= weekday <= 5:
        segments = _split_at_cuts(segments)

    result: list[tuple[int, int, str]] = []
    for start, end in segments:
        if end - start < MIN_MINUTES:
            continue  # 丢掉 10 分钟通勤之类的碎片
        is_evening = (
            1 <= weekday <= 5 and start >= EVENING_START and end <= EVENING_END
        )
        result.append((start, end, "evening" if is_evening else "free"))
    return result
