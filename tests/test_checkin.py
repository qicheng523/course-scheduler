"""打卡接口测试（D8，docs/API.md §3⑧；11-21 任务卡 §1）。

运行（项目根目录）：
    .venv\\Scripts\\python.exe -m pytest -q
    .venv\\Scripts\\python.exe -m pytest -q tests/test_checkin.py

每个测试用一个新的内存数据库（照 test_plan.py 的写法），**不碰 data/app.db**。
这里的重点只有一个：**幂等**——同一天同一个任务打两次，表里只能有 1 条记录。
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import get_session
from app.main import app
from app.models import Checkin, Task

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 任务卡 §5 的 5 条冻结任务（数字别改，和 test_plan.py / 验收机同一套）
SEED_TASKS = [
    dict(title="线性代数第二章习题", category="作业", duration_min=90, deadline="2026-11-20T23:59:00", priority=1),
    dict(title="指针练习 10 题", category="C语言", duration_min=60, deadline="2026-11-21T23:59:00", priority=1),
    dict(title="课表排程器 接口联调", category="项目", duration_min=120, deadline="2026-11-22T23:59:00", priority=2),
    dict(title="数组类题 5 道", category="刷题", duration_min=60, deadline="2026-11-22T23:59:00", priority=2),
    dict(title="CS50 第 3 讲 视频+笔记", category="CS50", duration_min=45, deadline="2026-11-22T23:59:00", priority=3),
]

CHECKIN_DATE = "2026-11-23"


def build_client() -> tuple[TestClient, object]:
    """造一个只有 5 条任务的内存库；返回 (测试客户端, 引擎) 方便直接查表。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for task in SEED_TASKS:
            session.add(Task(**task))
        session.commit()

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app), engine


@pytest.fixture(autouse=True)
def _clean_overrides():
    """每个测试结束后把数据库替换撤掉，避免影响别的测试。"""
    yield
    app.dependency_overrides.clear()


def checkin(client: TestClient, **payload):
    """发一次打卡请求（参数照合同写：task_id / date / note）。"""
    return client.patch("/api/checkin", json=payload)


def all_checkins(engine) -> list[Checkin]:
    with Session(engine) as session:
        return list(session.exec(select(Checkin)).all())


def test_打卡成功返回冻结字段():
    """第一次打卡：200 + created=true，字段名和合同一字不差。"""
    client, engine = build_client()
    response = checkin(client, task_id=1, date=CHECKIN_DATE)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"task_id", "date", "done_at", "note", "created"}
    assert body["task_id"] == 1
    assert body["date"] == CHECKIN_DATE
    assert body["created"] is True
    assert body["note"] is None, "不带 note 就该存 null"
    # done_at 是服务器时间、ISO 字符串
    assert "T" in body["done_at"]
    assert datetime.fromisoformat(body["done_at"]).year == datetime.now().year
    assert len(all_checkins(engine)) == 1


def test_重复打卡幂等_created变false且表里只有一条():
    """K1/K2/K3：完全相同的请求再发一次，仍然 200，但 created=false、不新增记录。"""
    client, engine = build_client()
    first = checkin(client, task_id=1, date=CHECKIN_DATE)
    second = checkin(client, task_id=1, date=CHECKIN_DATE)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    # 第二次返回的是已经存在的那条，不是新造的一条
    assert second.json()["done_at"] == first.json()["done_at"]
    assert second.json()["date"] == CHECKIN_DATE
    assert len(all_checkins(engine)) == 1, "重复打卡不许变成两条记录"


def test_任务不存在返回404中文():
    """K4：打一个不存在的 task → 404 + 任务不存在（不是 500）。"""
    client, engine = build_client()
    response = checkin(client, task_id=99999, date=CHECKIN_DATE)

    assert response.status_code == 404
    assert response.json()["detail"] == "任务不存在"
    assert all_checkins(engine) == []


@pytest.mark.parametrize("bad_date", ["2026/11/23", "2026-1-1", "20261123", "2026-02-30", "abc"])
def test_日期格式错误返回422中文(bad_date):
    """K5：日期写法不对 → 422，detail 是能给用户看的中文（例子是 2026-11-23）。"""
    client, engine = build_client()
    response = checkin(client, task_id=1, date=bad_date)

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "日期要写成 2026-11-23 这样的格式"
    assert all_checkins(engine) == []


def test_日期不是字符串也返回422中文():
    """§0 硬规矩：出错一律 {"detail": "中文说明"}，不能被 pydantic 换成英文列表。"""
    client, engine = build_client()
    response = checkin(client, task_id=1, date=20261123)  # 数字，不是字符串

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "日期要写成 2026-11-23 这样的格式"
    assert all_checkins(engine) == []


def test_task_id不是整数也返回422中文():
    """task_id 写成 "abc" → 422 + 中文说明，不是 500、也不是英文错误列表。"""
    client, engine = build_client()
    response = checkin(client, task_id="abc", date=CHECKIN_DATE)

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "任务 id 必须是整数"
    assert all_checkins(engine) == []


def test_同一任务不同天各算一条():
    """唯一约束是 (task_id, date)：隔天再打是新的完成记录，不是重复。"""
    client, engine = build_client()
    day1 = checkin(client, task_id=1, date="2026-11-23")
    day2 = checkin(client, task_id=1, date="2026-11-24")

    assert day1.json()["created"] is True
    assert day2.json()["created"] is True
    assert len(all_checkins(engine)) == 2


def test_note存下来_重复打卡不覆盖原记录():
    """note 可选；重复打卡只返回原记录，不会把 note 改掉，也不会多一条。"""
    client, engine = build_client()
    first = checkin(client, task_id=2, date=CHECKIN_DATE, note="写完一半")
    second = checkin(client, task_id=2, date=CHECKIN_DATE, note="改一下备注")

    assert first.status_code == 200, first.text
    assert first.json()["note"] == "写完一半"
    assert second.status_code == 200, second.text
    assert second.json()["created"] is False
    assert second.json()["note"] == "写完一半", "重复打卡不能改掉原来的备注"

    rows = all_checkins(engine)
    assert len(rows) == 1
    assert rows[0].note == "写完一半"
