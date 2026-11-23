"""周计划接口测试（D6，docs/API.md §3⑥/⑦）。

运行（项目根目录）：
    .venv\\Scripts\\python.exe -m pytest -q
    .venv\\Scripts\\python.exe -m pytest -q tests/test_plan.py

每个测试用一个新的内存数据库（照 test_slots.py 的写法），**不碰 data/app.db**。
数据用：19 门真实课 + 35 条固定事件 + 任务卡 §5 的 5 条冻结任务。
"""

import sys
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

# 任务卡 §5 的 5 条冻结任务（数字别改）
SEED_TASKS = [
    dict(title="线性代数第二章习题", category="作业", duration_min=90, deadline="2026-11-20T23:59:00", priority=1),
    dict(title="指针练习 10 题", category="C语言", duration_min=60, deadline="2026-11-21T23:59:00", priority=1),
    dict(title="课表排程器 接口联调", category="项目", duration_min=120, deadline="2026-11-22T23:59:00", priority=2),
    dict(title="数组类题 5 道", category="刷题", duration_min=60, deadline="2026-11-22T23:59:00", priority=2),
    dict(title="CS50 第 3 讲 视频+笔记", category="CS50", duration_min=45, deadline="2026-11-22T23:59:00", priority=3),
]


def build_client(extra_tasks=()) -> TestClient:
    """造一个 19 课 + 35 固定事件 + 5 条（+额外）任务的内存库。"""
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
        for task in [*SEED_TASKS, *extra_tasks]:
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


def signature(blocks: list[dict]) -> list[tuple]:
    """忽略 block id，只比较内容（确定性测试用）。"""
    return [
        (b["date"], b["start"], b["end"], b["kind"], b["task_id"], b["title"])
        for b in blocks
    ]


def test_generate_returns_frozen_fields_and_schedules_at_least_four():
    client = build_client()
    body = generate(client)

    assert set(body) == {"plan_id", "week_start", "blocks", "unscheduled", "stats"}
    assert body["week_start"] == WEEK_START
    assert isinstance(body["plan_id"], int)
    assert body["blocks"], "blocks 不能为空"
    assert {b["kind"] for b in body["blocks"]} <= {"course", "fixed", "task"}
    assert "free" not in {b["kind"] for b in body["blocks"]}
    assert body["stats"]["scheduled"] >= 4
    assert body["stats"]["scheduled"] + body["stats"]["unscheduled"] == 5


def test_no_overlap_between_blocks():
    body = generate(build_client())
    by_day: dict[str, list[tuple[int, int]]] = {}
    for block in body["blocks"]:
        by_day.setdefault(block["date"], []).append((to_min(block["start"]), to_min(block["end"])))

    for day, intervals in by_day.items():
        intervals.sort()
        for (start1, end1), (start2, _end2) in zip(intervals, intervals[1:]):
            assert start2 >= end1, f"{day} 有重叠：{start1}-{end1} 和 {start2} 开始"


def test_task_blocks_are_15_to_120_minutes():
    body = generate(build_client())
    task_blocks = [b for b in body["blocks"] if b["kind"] == "task"]
    assert task_blocks
    for block in task_blocks:
        minutes = to_min(block["end"]) - to_min(block["start"])
        assert 15 <= minutes <= 120, f"{block['start']}-{block['end']} 是 {minutes} 分钟"


def test_task_blocks_do_not_cross_evening_boundaries():
    body = generate(build_client())
    for block in body["blocks"]:
        if block["kind"] != "task":
            continue
        start, end = to_min(block["start"]), to_min(block["end"])
        assert not (start < 1140 < end), f"跨过 19:00：{block['start']}-{block['end']}"
        assert not (start < 1260 < end), f"跨过 21:00：{block['start']}-{block['end']}"
        assert (start, end) not in {(1130, 1140), (1260, 1270)}, f"落在通勤时间：{block}"


def test_regenerate_same_week_overwrites():
    client = build_client()
    first = generate(client)
    second = generate(client)

    assert len(second["blocks"]) == len(first["blocks"])
    assert second["stats"] == first["stats"]
    # GET 也是同一套（不会翻倍）
    got = client.get(f"/api/plan/{WEEK_START}")
    assert got.status_code == 200
    assert len(got.json()["blocks"]) == len(second["blocks"])


def test_get_plan_matches_generate_and_missing_week_returns_404():
    client = build_client()
    body = generate(client)

    got = client.get(f"/api/plan/{WEEK_START}")
    assert got.status_code == 200
    assert signature(got.json()["blocks"]) == signature(body["blocks"])
    assert got.json()["plan_id"] == body["plan_id"]

    missing = client.get("/api/plan/2026-12-07")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "这一周还没有计划"


def test_generate_is_deterministic():
    client = build_client()
    signatures = [signature(generate(client)["blocks"]) for _ in range(3)]
    assert signatures[0] == signatures[1] == signatures[2]


def test_unscheduled_task_has_reason():
    past_deadline = dict(
        title="上周就该交的作业",
        category="作业",
        duration_min=60,
        deadline="2026-11-10T23:59:00",
        priority=1,
    )
    body = generate(build_client(extra_tasks=[past_deadline]))

    unscheduled = body["unscheduled"]
    assert unscheduled, "过期任务必须进 unscheduled"
    item = next(item for item in unscheduled if item["title"] == "上周就该交的作业")
    assert item["reason"]
    assert "截止" in item["reason"]


def test_long_task_is_split_within_block_limits():
    long_task = dict(
        title="超长任务 150 分钟",
        category="项目",
        duration_min=150,
        deadline="2026-11-22T23:59:00",
        priority=3,
    )
    body = generate(build_client(extra_tasks=[long_task]))

    blocks = [b for b in body["blocks"] if b["kind"] == "task" and b["title"] == "超长任务 150 分钟"]
    assert len(blocks) >= 2, "150 分钟必须切成至少两块"
    minutes = [to_min(b["end"]) - to_min(b["start"]) for b in blocks]
    assert sum(minutes) == 150
    assert all(15 <= m <= 120 for m in minutes)


def test_blocks_include_done_field_default_false():
    client = build_client()
    body = generate(client)

    assert body["blocks"], "blocks 不能为空"
    for block in body["blocks"]:
        assert "done" in block, f"block 缺 done 字段：{block}"
        assert block["done"] is False, f"打卡前 done 应为 False：{block}"

    got = client.get(f"/api/plan/{WEEK_START}")
    assert got.status_code == 200
    for block in got.json()["blocks"]:
        assert "done" in block, f"GET 返回的 block 缺 done 字段：{block}"
        assert block["done"] is False, f"打卡前 done 应为 False：{block}"


def test_checkin_updates_block_done_to_true():
    client = build_client()
    body = generate(client)

    task_blocks = [b for b in body["blocks"] if b["kind"] == "task"]
    assert task_blocks, "计划里至少要有一个 task 块"
    first = task_blocks[0]
    tid, dt = first["task_id"], first["date"]
    assert tid is not None

    response = client.patch("/api/checkin", json={"task_id": tid, "date": dt})
    assert response.status_code == 200, response.text

    got = client.get(f"/api/plan/{WEEK_START}")
    assert got.status_code == 200
    blocks = got.json()["blocks"]

    marked = [
        b for b in blocks
        if b["kind"] == "task" and b["task_id"] == tid and b["date"] == dt
    ]
    assert marked, "打卡后应该还能在 blocks 里找到这个 task 块"
    assert all(b["done"] is True for b in marked), "打卡的那个块 done 应为 True"

    others = [
        b for b in blocks
        if b["kind"] == "task" and not (b["task_id"] == tid and b["date"] == dt)
    ]
    assert others, "还应有其他未打卡的 task 块"
    assert all(b["done"] is False for b in others), "其他未打卡 task 块 done 应为 False"
