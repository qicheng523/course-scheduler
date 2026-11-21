"""周统计 / 导出测试（D8，docs/API.md §3⑨/⑩；11-21 任务卡 §1）。

运行（项目根目录）：
    .venv\\Scripts\\python.exe -m pytest -q tests/test_stats_export.py

每个测试用一个新的内存数据库（照 test_plan.py 的写法），**不碰 data/app.db**。
数据用：19 门真实课 + 35 条固定事件 + 任务卡 §5 的 5 条冻结任务。
"""

import sys
from datetime import date as date_cls
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import Course, FixedEvent, Task

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.seed import FIXED_EVENTS, parse_seed_courses, to_min  # noqa: E402

SEED_PATH = ROOT / "data" / "seed-courses.txt"
WEEK_START = "2026-11-16"
WEEK_DAYS = [
    (date_cls.fromisoformat(WEEK_START) + timedelta(days=offset)).isoformat()
    for offset in range(7)
]

# 任务卡 §5 的 5 条冻结任务（数字别改）
SEED_TASKS = [
    dict(title="线性代数第二章习题", category="作业", duration_min=90, deadline="2026-11-20T23:59:00", priority=1),
    dict(title="指针练习 10 题", category="C语言", duration_min=60, deadline="2026-11-21T23:59:00", priority=1),
    dict(title="课表排程器 接口联调", category="项目", duration_min=120, deadline="2026-11-22T23:59:00", priority=2),
    dict(title="数组类题 5 道", category="刷题", duration_min=60, deadline="2026-11-22T23:59:00", priority=2),
    dict(title="CS50 第 3 讲 视频+笔记", category="CS50", duration_min=45, deadline="2026-11-22T23:59:00", priority=3),
]
CATEGORY_BY_TITLE = {task["title"]: task["category"] for task in SEED_TASKS}


def build_client() -> TestClient:
    """造一个 19 课 + 35 固定事件 + 5 条任务的内存库。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for course in parse_seed_courses(SEED_PATH):
            session.add(Course(**course))
        for name, weekday, start, end, note in FIXED_EVENTS:
            session.add(
                FixedEvent(
                    name=name,
                    weekday=weekday,
                    start_min=to_min(start),
                    end_min=to_min(end),
                    note=note or None,
                )
            )
        for task in SEED_TASKS:
            session.add(Task(**task))
        session.commit()

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


def generate(client: TestClient, week_start: str = WEEK_START) -> dict:
    response = client.post("/api/plan/generate", json={"week_start": week_start})
    assert response.status_code == 201, response.text
    return response.json()


def task_blocks_of(body: dict) -> list[dict]:
    return [block for block in body["blocks"] if block["kind"] == "task"]


def get_stats(client: TestClient, week_start: str = WEEK_START) -> dict:
    response = client.get("/api/stats/week", params={"week_start": week_start})
    assert response.status_code == 200, response.text
    return response.json()


def checkin(client: TestClient, task_id: int, day: str = "2026-11-17"):
    response = client.patch("/api/checkin", json={"task_id": task_id, "date": day})
    assert response.status_code == 200, response.text
    return response.json()


def test_没有计划的周统计返回404():
    """这一周没生成过计划 → 404 + 这一周还没有计划（不是空数字）。"""
    client = build_client()
    response = client.get("/api/stats/week", params={"week_start": "2027-01-04"})

    assert response.status_code == 404
    assert response.json()["detail"] == "这一周还没有计划"


def test_totals四个指标齐全且和计划一致():
    """T1：totals 固定 4 个键；数字能和 generate 的块对上。"""
    client = build_client()
    body = generate(client)
    stats = get_stats(client)

    assert set(stats) == {"week_start", "totals", "by_day", "by_category"}
    assert stats["week_start"] == WEEK_START
    totals = stats["totals"]
    assert set(totals) == {"scheduled", "done", "unscheduled", "planned_minutes"}

    blocks = task_blocks_of(body)
    assert totals["scheduled"] == len({block["task_id"] for block in blocks})
    assert totals["planned_minutes"] == sum(to_min(b["end"]) - to_min(b["start"]) for b in blocks)
    assert totals["scheduled"] + totals["unscheduled"] == len(SEED_TASKS)
    assert totals["done"] == 0, "还没打卡，完成数必须是 0"


def test_by_day永远7条_连续升序():
    """T2：by_day 恒 7 条，从 week_start 起连续七天，哪怕那天没任务也要出现。"""
    client = build_client()
    generate(client)
    by_day = get_stats(client)["by_day"]

    assert len(by_day) == 7
    assert [row["date"] for row in by_day] == WEEK_DAYS
    for row in by_day:
        assert set(row) == {"date", "tasks", "done", "minutes"}
        assert row["tasks"] >= 0
        assert row["done"] == 0
        assert row["minutes"] >= 0


def test_打卡后done变成1_重复打卡不再增加():
    """T3：打卡一次 done=1；再打一次还是 1（幂等，不是 2）。"""
    client = build_client()
    body = generate(client)
    first_task = task_blocks_of(body)[0]["task_id"]

    checkin(client, first_task, "2026-11-17")
    assert get_stats(client)["totals"]["done"] == 1

    checkin(client, first_task, "2026-11-17")
    assert get_stats(client)["totals"]["done"] == 1, "重复打卡不能把完成数变成 2"


def test_by_category只列本周出现过的类别且按分钟降序():
    """按类汇总：类别只算本周真排进去的任务，time 从大到小排，数字对得上。"""
    client = build_client()
    body = generate(client)
    by_category = get_stats(client)["by_category"]

    expected: dict[str, set] = {}
    for block in task_blocks_of(body):
        expected.setdefault(CATEGORY_BY_TITLE[block["title"]], set()).add(block["task_id"])

    assert {row["category"] for row in by_category} == set(expected)
    assert {row["category"]: row["tasks"] for row in by_category} == {
        category: len(ids) for category, ids in expected.items()
    }
    minutes = [row["minutes"] for row in by_category]
    assert minutes == sorted(minutes, reverse=True), "by_category 要按 minutes 从大到小"
    assert all(row["done"] == 0 for row in by_category)


def test_by_day的done记在任务被安排的那天():
    """by_day.done 记在"任务被安排的那一天"，并且 by_day 之和 = totals.done。

    打卡日期故意选一个不是任务安排日期的日子（2026-11-17），
    确认数字不会跑到打卡那一天去（否则会出现"0 个任务却完成 1 个"的行）。
    """
    client = build_client()
    body = generate(client)
    target = task_blocks_of(body)[0]

    checkin(client, target["task_id"], "2026-11-17")

    stats = get_stats(client)
    by_day = {row["date"]: row for row in stats["by_day"]}
    assert by_day[target["date"]]["done"] == 1
    assert sum(row["done"] for row in stats["by_day"]) == stats["totals"]["done"] == 1


def test_导出Markdown结构与内容():
    """E1/E2/E3：200 + text/markdown + 冻结标题 + 7 天小节 + 没安排的那天也有小节。"""
    client = build_client()
    body = generate(client)
    response = client.get("/api/export.md", params={"week_start": WEEK_START})

    assert response.status_code == 200, response.text
    content_type = response.headers["content-type"]
    assert "text/markdown" in content_type
    assert "charset=utf-8" in content_type
    assert 'filename="export-2026-11-16.md"' in response.headers["content-disposition"]

    text = response.text
    assert "# 课表排程周报" in text
    assert f"{WEEK_START} ~ {WEEK_DAYS[-1]}" in text
    for heading in ("## 概览", "## 每天安排", "## 没排下的任务", "## 打卡记录"):
        assert heading in text
    assert text.count("### ") == 7, "七天小节一天都不能少"

    task_blocks = task_blocks_of(body)
    assert "已排任务：" in text
    assert f"已排任务：{len({b['task_id'] for b in task_blocks})} 个" in text
    # 有些天没有任务 → 必须写 "- （没有安排）"，不许省略这一天
    days_with_tasks = {block["date"] for block in task_blocks}
    if len(days_with_tasks) < 7:
        assert "（没有安排）" in text

    # 已排的任务行形如 "- 19:00–20:30 标题"
    first = task_blocks[0]
    assert f"- {first['start']}–{first['end']} {first['title']}" in text


def test_导出里打卡有勾选和打卡记录():
    """E2：打了卡的任务后面加 ✅，并在「打卡记录」里出现。"""
    client = build_client()
    body = generate(client)
    target = task_blocks_of(body)[0]
    checkin(client, target["task_id"], "2026-11-17")

    text = client.get("/api/export.md", params={"week_start": WEEK_START}).text
    assert f"- {target['start']}–{target['end']} {target['title']} ✅" in text

    record_section = text.split("## 打卡记录", 1)[1]
    assert f"- 2026-11-17 {target['title']}" in record_section


def test_没有计划的周导出返回404():
    """E4：没有计划的周 → 404 中文，不许返回空文件。"""
    client = build_client()
    response = client.get("/api/export.md", params={"week_start": "2027-01-04"})

    assert response.status_code == 404
    assert response.json()["detail"] == "这一周还没有计划"
