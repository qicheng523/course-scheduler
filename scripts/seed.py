"""灌种子数据：把 19 条真实课表 + 固定事件写进 data/app.db。

用法（在项目根目录）：
    python scripts/seed.py

干了什么（按顺序）：
1. 读 data/seed-courses.txt（B 维护的唯一数据源），解析成课程列表；
2. 加上文件顶部的固定事件清单（睡觉、三餐、英语班，改作息只改那里）；
3. 先清空 course / fixed_event 两张表，再写入新数据
   ——重复跑不会越灌越多（这叫"幂等"）。

字段约定以 docs/API.md §1 为准：
- 课程没有"教师"字段，txt 里的"老师A~H"只做脱敏记录，不进数据库；
- 数据库存分钟整数，这里统一用 "HH:mm" 写，脚本负责转换；
- 第 9 节（18:00-20:35）是晚自习 = 空闲时间，不是课程，所以不在这里。
"""

import sys
from pathlib import Path

# 把项目根目录放进导入路径：不管在哪个目录执行，都能 import app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import Session, select  # noqa: E402

from app.db import DB_PATH, create_db_and_tables, engine  # noqa: E402
from app.models import Course, FixedEvent  # noqa: E402

TERM = "2026f"  # 学期，docs/API.md §1 固定用这个

# ---------------------------------------------------------------- 固定事件
# 想改作息就改这里。格式：(名称, 星期, 开始, 结束, 备注)
# 星期：1=周一 … 7=周日；时间 "HH:mm"；一天内开始必须早于结束。
# 跨天的时间（如睡觉 23:00-07:00）要拆成两行，因为模型不支持跨午夜。
FIXED_EVENTS = [
    *[("睡觉", d, "00:00", "07:30", "凌晨段（跨天拆出的前半段）") for d in range(1, 8)],
    *[("睡觉", d, "23:00", "24:00", "晚上段（跨天拆出的后半段）") for d in range(1, 8)],
    *[("早饭", d, "07:30", "08:00", "上课前") for d in range(1, 6)],
    *[("午饭", d, "12:00", "12:50", "") for d in range(1, 6)],
    *[("午休", d, "12:50", "14:00", "中午小睡；想让排程用这段时间就删掉这几行") for d in range(1, 6)],
    *[("晚饭", d, "18:00", "18:30", "之后到晚自习结束是空闲") for d in range(1, 6)],
    ("英语班", 6, "09:00", "11:30", "按你的真实时间改"),
]

# ---------------------------------------------------------------- 时间模型
# 九节时间表逐节写死（TEAM.md §4.3：禁止用公式推，间隔不均匀）。
# 第 9 节 18:00-20:35 是晚自习（空闲），不是课程，所以表里没有它。
WEEKDAYS = {"周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7}

PERIOD_TIMES = {
    "1-2": ("08:00", "09:40"),
    "3-4": ("10:10", "11:50"),
    "5-6": ("14:00", "15:40"),
    "7-8": ("16:10", "17:50"),
}

# ---------------------------------------------------------------- 小工具

def to_min(hhmm: str) -> int:
    """把 "08:00" 转成 480（数据库存的是分钟整数）。"""
    hour_text, minute_text = hhmm.split(":")
    return int(hour_text) * 60 + int(minute_text)


def parse_seed_courses(path: Path) -> list[dict]:
    """解析 data/seed-courses.txt，返回 19 条课程（每行一节课）。

    行格式：星期 节次 课程名 地点 老师
    例：周一 1-2 中国近现代史纲要 28-A303 老师A
    行首 # 是注释；老师列只用来脱敏记录，不进数据库。
    """
    courses: list[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 4:
            raise SystemExit(f"[!] {path.name} 第 {lineno} 行格式不对（至少要 4 段）：{line}")
        weekday_text, periods = parts[0], parts[1]
        teacher = parts[-1]        # 最后一段：老师X（只做脱敏记录）
        location = parts[-2]       # 倒数第二段：地点
        name = " ".join(parts[2:-2])  # 中间全算课程名

        if weekday_text not in WEEKDAYS:
            raise SystemExit(f"[!] {path.name} 第 {lineno} 行星期看不懂：{weekday_text}")
        if periods not in PERIOD_TIMES:
            raise SystemExit(f"[!] {path.name} 第 {lineno} 行节次不认识（只认 1-2/3-4/5-6/7-8）：{periods}")
        if not teacher.startswith("老师"):
            print(f"[warn] 第 {lineno} 行最后一段不是\"老师X\"格式，直接忽略：{teacher}")

        start, end = PERIOD_TIMES[periods]
        courses.append(
            {
                "name": name,
                "weekday": WEEKDAYS[weekday_text],
                "start_min": to_min(start),
                "end_min": to_min(end),
                "location": location,
                "term": TERM,
            }
        )
    return courses


def clear_and_seed(courses: list[dict], fixed_events: list[tuple]) -> None:
    """先清空 course / fixed_event 两张表，再写入新的（幂等）。"""
    with Session(engine) as session:
        old_courses = session.exec(select(Course)).all()
        old_events = session.exec(select(FixedEvent)).all()
        for row in old_courses:
            session.delete(row)
        for row in old_events:
            session.delete(row)
        session.commit()
        print(f"[1/3] 清掉旧数据：课程 {len(old_courses)} 条、固定事件 {len(old_events)} 条")

        for c in courses:
            session.add(Course(**c))
        for name, weekday, start, end, note in fixed_events:
            session.add(
                FixedEvent(
                    name=name,
                    weekday=weekday,
                    start_min=to_min(start),
                    end_min=to_min(end),
                    note=note or None,
                )
            )
        session.commit()
        print(f"[2/3] 写入：课程 {len(courses)} 条、固定事件 {len(fixed_events)} 条")
        print(f"[3/3] 数据库：{DB_PATH}")


def main() -> int:
    create_db_and_tables()

    seed_path = PROJECT_ROOT / "data" / "seed-courses.txt"
    courses = parse_seed_courses(seed_path)
    if len(courses) != 19:
        print(f"[warn] txt 里解析出 {len(courses)} 条课程，预期是 19 条（docs/API.md §4）")

    clear_and_seed(courses, FIXED_EVENTS)

    print("\n灌完了。启动网站后打开 http://127.0.0.1:8000/api/courses 应该看到 total=19。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
