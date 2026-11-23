"""周计划接口测试（D6，docs/API.md §3⑥/⑦）。

运行（项目根目录）：
    .venv\\Scripts\\python.exe -m pytest -q
    .venv\\Scripts\\python.exe -m pytest -q tests/test_plan.py

每个测试用一个新的内存数据库（照 test_slots.py 的写法），**不碰 data/app.db**。
数据用：19 门真实课 + 35 条固定事件 + 任务卡 §5 的 5 条冻结任务。
"""

import sys
from datetime import date as date_cls
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import get_session
from app.main import app
from app.models import Block, Checkin, Course, FixedEvent, Plan, Task

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
    engine = _build_engine(extra_tasks)

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app)


def _build_engine(extra_tasks=()):
    """共享的建库逻辑：build_client / build_client_with_db 都用它。"""
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

    return engine


def build_client_with_db(extra_tasks=()):
    """同 build_client，但把内存 engine 一起返回，方便测试直接查库。"""
    engine = _build_engine(extra_tasks)

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app), engine


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


# ---------------------------------------------------------------- 11-24 新增（v0.8 §3⑪⑫⑬）

def _hhmm(minutes: int) -> str:
    """把分钟数转回 "HH:mm"（测试里自己算空闲段用）。"""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _find_free_slot(blocks: list[dict], target: dict, duration: int = 30):
    """在 target 同一天找一段不重叠、不跨晚自习、够 duration 分钟的空档。

    返回 (start, end) 两个 "HH:mm" 字符串；找不到返回 None。
    只用于 PATCH 的正常用例——挑一个肯定合法的目标时间。
    """
    date = target["date"]
    weekday = date_cls.fromisoformat(date).isoweekday()
    occupied = sorted(
        (to_min(b["start"]), to_min(b["end"]))
        for b in blocks
        if b["date"] == date and b["id"] != target["id"]
    )
    for start in range(450, 1290 - duration + 1, 15):
        end = start + duration
        if weekday <= 5 and ((start < 1140 < end) or (start < 1260 < end)):
            continue
        if any(start < oe and end > os for os, oe in occupied):
            continue
        return _hhmm(start), _hhmm(end)
    return None


def test_delete_plan_clears_everything_and_restores_task_status():
    extra = dict(
        title="待恢复状态的任务",
        category="作业",
        duration_min=30,
        deadline="2026-11-22T23:59:00",
        priority=1,
        status="scheduled",
    )
    client, engine = build_client_with_db(extra_tasks=[extra])
    body = generate(client)

    scheduled_extra = [b for b in body["blocks"] if b["title"] == "待恢复状态的任务"]
    assert scheduled_extra, "额外的 scheduled 任务应该被排进计划"
    tid = scheduled_extra[0]["task_id"]
    dt = scheduled_extra[0]["date"]
    assert tid is not None

    # 打一次卡，好验证删除时打卡被一起清掉
    assert client.patch("/api/checkin", json={"task_id": tid, "date": dt}).status_code == 200

    resp = client.delete(f"/api/plan/{WEEK_START}")
    assert resp.status_code == 204

    got = client.get(f"/api/plan/{WEEK_START}")
    assert got.status_code == 404
    assert got.json()["detail"] == "这一周还没有计划"

    # 直接查内存库：plan / block / checkin 全清空，排过的任务回到 todo
    with Session(engine) as s:
        assert s.exec(select(Plan)).all() == []
        assert s.exec(select(Block)).all() == []
        assert s.exec(select(Checkin)).all() == []
        restored = s.get(Task, tid)
        assert restored is not None
        assert restored.status == "todo"


def test_delete_plan_missing_week_returns_404():
    client = build_client()
    resp = client.delete("/api/plan/2026-12-07")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "这一周还没有计划"


def test_create_and_list_tasks():
    client = build_client()
    payload = {
        "title": "线性代数第三章",
        "category": "作业",
        "duration_min": 60,
        "deadline": "2026-11-25T23:59:00",
        "priority": 2,
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert isinstance(created["id"], int)
    assert created["status"] == "todo"
    assert created["title"] == "线性代数第三章"
    assert created["category"] == "作业"
    assert created["duration_min"] == 60
    assert created["deadline"] == "2026-11-25T23:59:00"
    assert created["priority"] == 2

    got = client.get("/api/tasks")
    assert got.status_code == 200
    data = got.json()
    assert data["total"] == 6  # 5 seed + 1 新增
    assert [t["title"] for t in data["items"]].count("线性代数第三章") == 1

    # 按状态过滤：新任务和 5 条 seed 都是 todo
    todo = client.get("/api/tasks", params={"status": "todo"})
    assert todo.status_code == 200
    assert todo.json()["total"] == 6
    done = client.get("/api/tasks", params={"status": "done"})
    assert done.status_code == 200
    assert done.json()["total"] == 0


def test_create_task_validations():
    client = build_client()
    cases = [
        ({"title": "   ", "category": "作业", "duration_min": 60, "deadline": "2026-11-25T23:59:00", "priority": 2}, "任务名不能为空"),
        ({"title": "任务", "category": "作业", "duration_min": 0, "deadline": "2026-11-25T23:59:00", "priority": 2}, "预计用时要大于 0 分钟"),
        ({"title": "任务", "category": "作业", "duration_min": 60, "deadline": "2026-11-25T23:59:00", "priority": 4}, "优先级只能是 1、2、3"),
        ({"title": "任务", "category": "游戏", "duration_min": 60, "deadline": "2026-11-25T23:59:00", "priority": 2}, "类别只能是 作业 / C语言 / 项目 / 刷题 / CS50"),
        ({"title": "任务", "category": "作业", "duration_min": 60, "deadline": "2026/11/25 23:59", "priority": 2}, "截止时间要写成 2026-11-25T23:59:00 这样的格式"),
    ]
    for payload, detail in cases:
        resp = client.post("/api/tasks", json=payload)
        assert resp.status_code == 422, resp.text
        assert resp.json()["detail"] == detail


def test_delete_task_block():
    client = build_client()
    body = generate(client)
    task_blocks = [b for b in body["blocks"] if b["kind"] == "task"]
    assert task_blocks
    target = task_blocks[0]

    resp = client.delete(f"/api/block/{target['id']}")
    assert resp.status_code == 204

    got = client.get(f"/api/plan/{WEEK_START}")
    assert got.status_code == 200
    ids = [b["id"] for b in got.json()["blocks"]]
    assert target["id"] not in ids


def test_delete_block_errors():
    client = build_client()
    resp = client.delete("/api/block/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "这个时间块不存在"

    body = generate(client)
    course = next(b for b in body["blocks"] if b["kind"] == "course")
    resp = client.delete(f"/api/block/{course['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "课和固定事件不能改"


def test_patch_block_updates_time():
    client = build_client()
    body = generate(client)
    task_blocks = [b for b in body["blocks"] if b["kind"] == "task"]
    assert task_blocks

    target = None
    new_start = new_end = None
    for candidate in task_blocks:
        slot = _find_free_slot(body["blocks"], candidate)
        if slot is not None:
            target = candidate
            new_start, new_end = slot
            break
    assert target is not None, "找不到一个能移动的任务块"

    resp = client.patch(
        f"/api/block/{target['id']}", json={"start": new_start, "end": new_end}
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["id"] == target["id"]
    assert updated["start"] == new_start
    assert updated["end"] == new_end
    assert "done" in updated

    # GET plan 里也同步更新了
    got = client.get(f"/api/plan/{WEEK_START}")
    block = next(b for b in got.json()["blocks"] if b["id"] == target["id"])
    assert block["start"] == new_start
    assert block["end"] == new_end


def test_patch_block_validations():
    client = build_client()
    body = generate(client)
    task_blocks = [b for b in body["blocks"] if b["kind"] == "task"]
    assert task_blocks
    target = task_blocks[0]

    # 1. 超出 07:30–21:30
    resp = client.patch(f"/api/block/{target['id']}", json={"start": "07:00", "end": "08:00"})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "时间要落在 07:30–21:30 之内"

    # 2. 时长不足 15 分钟
    resp = client.patch(f"/api/block/{target['id']}", json={"start": "08:00", "end": "08:10"})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "任务块要在 15–120 分钟之间"

    # 3. 跨 19:00（晚自习边界只在工作日校验）
    weekday_target = next(
        (b for b in task_blocks if date_cls.fromisoformat(b["date"]).isoweekday() <= 5),
        target,
    )
    resp = client.patch(
        f"/api/block/{weekday_target['id']}", json={"start": "18:30", "end": "19:30"}
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "任务块不能跨过晚自习边界"

    # 4. 与同一天课程重叠 → 409，带课名
    course = next(
        b for b in body["blocks"]
        if b["kind"] == "course" and b["date"] == weekday_target["date"]
    )
    resp = client.patch(
        f"/api/block/{weekday_target['id']}",
        json={"start": course["start"], "end": course["end"]},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == f"这个时间和「{course['title']}」重叠"
