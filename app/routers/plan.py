"""空闲段接口（docs/API.md §3⑤，D3）。

    GET /api/slots?date=2026-11-19

只做三件事：
1. 校验日期格式（错 → 422 中文 detail）；
2. 从数据库取"那天"的课 + 固定事件；
3. 交给 app/services/slots.py 的纯函数算空闲段，拼成冻结好的 JSON。

算法本身一行都不写在这里——这样测试可以直接测纯函数，不用起网页。
"""

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import Course, FixedEvent
from app.services.slots import free_segments, to_hhmm

router = APIRouter(tags=["空闲段"])

TERM = "2026f"
# 只认 2026-11-19 这种格式（"2026/11/19"、"2026-1-9" 都拒绝）
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/api/slots")
def get_slots(
    date: str = Query(description="要查的日期，格式 2026-11-19"),
    session: Session = Depends(get_session),
) -> dict:
    """查某一天的空闲段（返回格式见 docs/API.md §3⑤）。"""
    if not isinstance(date, str) or DATE_PATTERN.match(date) is None:
        raise HTTPException(status_code=422, detail="日期要写成 2026-11-19 这样的格式")
    try:
        parsed = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail="日期要写成 2026-11-19 这样的格式")

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
