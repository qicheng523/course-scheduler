"""课程接口的自动检查（D2 过线：加课能用、写错报错、重叠报错）。

运行（项目根目录）：python -m pytest -q
成功标志：最后一行是 "5 passed"（或更多）。

每个测试用一个新的内存数据库，**不碰 data/app.db**，所以可以随便跑。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app

# 一条合法的课程，冲突测试里改几个字段就变成另一门课
COURSE = {
    "name": "高等数学AI",
    "weekday": 1,
    "start": "08:00",
    "end": "09:40",
    "location": "1-0206",
}


def make_payload(**overrides) -> dict:
    """返回一份课程数据，overrides 里写要改的字段。"""
    data = dict(COURSE)
    data.update(overrides)
    return data


@pytest.fixture(name="client")
def client_fixture():
    """给每个测试准备一个干净的内存数据库，并把接口的数据库会话换过去。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_create_and_list_course(client: TestClient) -> None:
    """能加课；加完能在列表里查到；时间返回 "HH:mm"；id 是整数。"""
    created = client.post("/api/courses", json=make_payload())
    assert created.status_code == 201

    body = created.json()
    assert body["name"] == "高等数学AI"
    assert body["weekday"] == 1
    assert body["start"] == "08:00"
    assert body["end"] == "09:40"
    assert isinstance(body["id"], int)

    listed = client.get("/api/courses", params={"term": "2026f"})
    assert listed.status_code == 200
    data = listed.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == body["id"]


def test_invalid_weekday_and_time_return_422(client: TestClient) -> None:
    """星期不在 1–5、时间格式不对、结束早于开始，都必须 422 且中文提示。"""
    bad_weekday = client.post("/api/courses", json=make_payload(weekday=6))
    assert bad_weekday.status_code == 422
    assert "星期" in bad_weekday.json()["detail"]

    bad_format = client.post("/api/courses", json=make_payload(start="8:00"))
    assert bad_format.status_code == 422
    assert "08:00" in bad_format.json()["detail"]

    reversed_time = client.post(
        "/api/courses", json=make_payload(start="10:00", end="09:00")
    )
    assert reversed_time.status_code == 422
    assert "结束时间" in reversed_time.json()["detail"]

    # 一条都不该写进数据库
    assert client.get("/api/courses").json()["total"] == 0


def test_overlap_returns_409_with_course_name(client: TestClient) -> None:
    """时间重叠 → 409，detail 里要带冲突课程名；首尾相接不算重叠。"""
    assert client.post("/api/courses", json=make_payload()).status_code == 201

    conflict = client.post(
        "/api/courses",
        json=make_payload(name="线性代数", start="09:00", end="10:30"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "这门课和「高等数学AI」时间冲突"

    # 09:40 开始、和上一门首尾相接：允许
    touching = client.post(
        "/api/courses",
        json=make_payload(name="线性代数", start="09:40", end="11:10"),
    )
    assert touching.status_code == 201


def test_update_into_conflict_returns_409(client: TestClient) -> None:
    """把一门课改成和另一门课重叠，也要 409。"""
    first = client.post("/api/courses", json=make_payload()).json()
    second = client.post(
        "/api/courses",
        json=make_payload(name="线性代数", start="10:00", end="11:40"),
    ).json()
    assert first["id"] != second["id"]

    conflict = client.put(
        f"/api/courses/{second['id']}",
        json=make_payload(name="线性代数", start="09:00", end="10:30"),
    )
    assert conflict.status_code == 409
    assert "高等数学AI" in conflict.json()["detail"]


def test_update_ignores_itself_and_delete(client: TestClient) -> None:
    """改课不能和自己比冲突；改完能生效；删掉后 404。"""
    created = client.post("/api/courses", json=make_payload()).json()
    course_id = created["id"]

    # 原样改一遍（时间没变）不应该报冲突
    updated = client.put(f"/api/courses/{course_id}", json=make_payload(name="高等数学AI（改）"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "高等数学AI（改）"

    deleted = client.delete(f"/api/courses/{course_id}")
    assert deleted.status_code == 204

    assert client.delete(f"/api/courses/{course_id}").status_code == 404
    assert client.put(f"/api/courses/{course_id}", json=make_payload()).status_code == 404
