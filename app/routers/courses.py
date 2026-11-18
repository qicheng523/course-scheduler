"""课程接口：查 / 加 / 改 / 删（docs/API.md §2、§3）。

三条约定（别改）：
1. 数据库里的时间一律是"分钟整数"（08:00 → 480）；
   接口上的时间是 "HH:mm" 字符串；**转换只在这个文件里做**。
2. 出错统一返回 {"detail": "中文说明"}，这句中文会直接显示给用户看。
3. 星期只有 1–5（周一到周五）；6/7 拒绝（周末没有课）。

调用链：app/main.py 里 include_router → 这里的函数 → Course 表。
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, SQLModel, select

from app.db import get_session
from app.models import Course

router = APIRouter(prefix="/api/courses", tags=["课程"])

DEFAULT_TERM = "2026f"

# 只接受 "HH:mm"：小时 00–23，分钟 00–59。像 "8:00"（少一位）也会被拒绝。
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class CourseIn(SQLModel):
    """网页提交上来的课程（时间还是字符串，还没转成分钟）。"""

    name: str
    weekday: int
    start: str
    end: str
    location: str | None = None


# ---------------------------------------------------------------- 小工具

def parse_hhmm(value: str) -> int:
    """把 "08:00" 转成 480；格式不对直接报 422（中文 detail）。"""
    if not isinstance(value, str) or TIME_PATTERN.match(value) is None:
        raise HTTPException(status_code=422, detail="时间要写成 08:00 这样的格式")
    hour_text, minute_text = value.split(":")
    return int(hour_text) * 60 + int(minute_text)


def format_hhmm(minutes: int) -> str:
    """把 480 转回 "08:00"。"""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def course_to_dict(course: Course) -> dict:
    """把数据库里的课程转成接口返回的格式（时间变回 "HH:mm"）。"""
    return {
        "id": course.id,
        "name": course.name,
        "weekday": course.weekday,
        "start": format_hhmm(course.start_min),
        "end": format_hhmm(course.end_min),
        "location": course.location,
    }


def validated_course(payload: CourseIn) -> tuple[str, int, int, str | None]:
    """校验网页交上来的字段，返回（课程名, 开始分钟, 结束分钟, 地点）。

    任何一条不合法就抛 422，detail 是给用户看的中文。
    """
    if payload.weekday < 1 or payload.weekday > 5:
        raise HTTPException(status_code=422, detail="星期只能是 1 到 5（周六周日没有课）")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="课程名不能为空")
    if len(name) > 40:
        raise HTTPException(status_code=422, detail="课程名最多 40 个字")

    start_min = parse_hhmm(payload.start)
    end_min = parse_hhmm(payload.end)
    if end_min <= start_min:
        raise HTTPException(status_code=422, detail="结束时间必须晚于开始时间")

    location = payload.location.strip() if payload.location else None
    return name, start_min, end_min, location or None


def find_overlap(
    session: Session,
    weekday: int,
    start_min: int,
    end_min: int,
    exclude_id: int | None = None,
) -> Course | None:
    """找同一星期、同一学期、时间重叠的已有课程；没有就返回 None。

    重叠判断：start < 对方的 end 并且 end > 对方的 start。
    首尾相接不算重叠（例如 09:40 结束、09:40 开始可以）。
    """
    statement = select(Course).where(
        Course.term == DEFAULT_TERM,
        Course.weekday == weekday,
    )
    for other in session.exec(statement).all():
        if exclude_id is not None and other.id == exclude_id:
            continue  # 改课的时候，不要和自己比
        if start_min < other.end_min and end_min > other.start_min:
            return other
    return None


# ---------------------------------------------------------------- 4 个接口

@router.get("")
def list_courses(
    term: str = Query(default=DEFAULT_TERM, description="学期，默认 2026f"),
    session: Session = Depends(get_session),
) -> dict:
    """① 查课程：按星期、开始时间排好，时间返回 "HH:mm"。"""
    courses = session.exec(
        select(Course)
        .where(Course.term == term)
        .order_by(Course.weekday, Course.start_min)
    ).all()
    items = [course_to_dict(course) for course in courses]
    return {"items": items, "total": len(items)}


@router.post("", status_code=201)
def create_course(
    payload: CourseIn,
    session: Session = Depends(get_session),
) -> dict:
    """② 新增课程：成功 201，返回带 id 的整条记录。"""
    name, start_min, end_min, location = validated_course(payload)

    overlap = find_overlap(session, payload.weekday, start_min, end_min)
    if overlap is not None:
        raise HTTPException(
            status_code=409,
            detail=f"这门课和「{overlap.name}」时间冲突",
        )

    course = Course(
        name=name,
        weekday=payload.weekday,
        start_min=start_min,
        end_min=end_min,
        location=location,
        term=DEFAULT_TERM,
    )
    session.add(course)
    session.commit()
    session.refresh(course)
    return course_to_dict(course)


@router.put("/{course_id}")
def update_course(
    course_id: int,
    payload: CourseIn,
    session: Session = Depends(get_session),
) -> dict:
    """③ 修改课程：body 和新增一样（整体替换），成功 200。"""
    course = session.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    name, start_min, end_min, location = validated_course(payload)

    overlap = find_overlap(
        session, payload.weekday, start_min, end_min, exclude_id=course_id
    )
    if overlap is not None:
        raise HTTPException(
            status_code=409,
            detail=f"这门课和「{overlap.name}」时间冲突",
        )

    course.name = name
    course.weekday = payload.weekday
    course.start_min = start_min
    course.end_min = end_min
    course.location = location
    session.add(course)
    session.commit()
    session.refresh(course)
    return course_to_dict(course)


@router.delete("/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    session: Session = Depends(get_session),
) -> Response:
    """④ 删除课程：成功 204（没有内容），不存在 404。"""
    course = session.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")

    session.delete(course)
    session.commit()
    return Response(status_code=204)
