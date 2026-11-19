"""空闲段接口测试（D3，docs/API.md §3⑤）。

运行（项目根目录）：
    .venv\\Scripts\\python.exe -m pytest -q
    .venv\\Scripts\\python.exe -m pytest -q -k "晚自习 or 通勤 or 周末"

每个测试用一个新的内存数据库（照 test_courses.py 的写法），**不碰 data/app.db**。
数据用 B 的真课表 + 固定事件，保证和验收答案表是同一套数据。
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import Course, FixedEvent
from app.services.slots import free_segments

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.seed import FIXED_EVENTS, parse_seed_courses, to_min  # noqa: E402

SEED_PATH = ROOT / "data" / "seed-courses.txt"


def build_client(with_fixed: bool) -> TestClient:
    """造一个只有 19 门课（with_fixed=False）或课+固定事件（True）的内存库。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for course in parse_seed_courses(SEED_PATH):
            session.add(Course(**course))
        if with_fixed:
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
        session.commit()

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides():
    """每个测试结束后把数据库替换撤掉，避免影响别的测试。"""
    yield
    app.dependency_overrides.clear()


def get_segments(client: TestClient, date: str):
    """发请求并转成 [(开始分钟, 结束分钟, kind), ...]。"""
    response = client.get("/api/slots", params={"date": date})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["date"] == date
    assert body["total"] == len(body["items"])
    got = [(to_min(item["start"]), to_min(item["end"]), item["kind"]) for item in body["items"]]
    return body, got


def test_周四只有课是7段():
    """场景 1：周四只有 19 门课，7 段（冻结答案表第 1 行）。"""
    body, got = get_segments(build_client(with_fixed=False), "2026-11-19")
    assert body["weekday"] == 4
    assert got == [
        (450, 480, "free"),
        (580, 610, "free"),
        (710, 840, "free"),
        (940, 970, "free"),
        (1070, 1130, "free"),
        (1140, 1260, "evening"),
        (1270, 1290, "free"),
    ]


def test_周四课加固定事件是5段():
    """场景 2：周四课 + 35 条固定事件，5 段（真库答案）。"""
    body, got = get_segments(build_client(with_fixed=True), "2026-11-19")
    assert body["weekday"] == 4
    assert got == [
        (580, 610, "free"),
        (940, 970, "free"),
        (1110, 1130, "free"),
        (1140, 1260, "evening"),
        (1270, 1290, "free"),
    ]


def test_晚自习是独立的一段():
    """19:00–21:00 必须单独成段、kind=evening，且只有这一段是 evening。"""
    body, got = get_segments(build_client(with_fixed=True), "2026-11-19")
    evening = [(start, end) for start, end, kind in got if kind == "evening"]
    assert evening == [(1140, 1260)]
    items = body["items"]
    assert any(i["start"] == "19:00" and i["end"] == "21:00" and i["kind"] == "evening" for i in items)
    assert sum(1 for i in items if i["kind"] == "evening") == 1


def test_通勤碎片被丢掉():
    """18:50–19:00、21:00–21:10 两段 10 分钟通勤不许出现。"""
    body, got = get_segments(build_client(with_fixed=True), "2026-11-19")
    assert (1130, 1140) not in got
    assert (1260, 1270) not in got
    for start, end, _kind in got:
        # 也不许有一段跨过 19:00 或 21:00
        assert not (start < 1140 < end)
        assert not (start < 1260 < end)


def test_周末不被晚自习切开():
    """周六有英语班 09:00–11:30：只剩两段，且第二段跨过 19:00–21:00 不切。"""
    body, got = get_segments(build_client(with_fixed=True), "2026-11-21")
    assert body["weekday"] == 6
    assert got == [(450, 540, "free"), (690, 1290, "free")]
    assert all(kind == "free" for _start, _end, kind in got)


def test_周六只有课是一整段():
    """周六没有课：07:30–21:30 一整段，说明周末不切四点。"""
    _body, got = get_segments(build_client(with_fixed=False), "2026-11-21")
    assert got == [(450, 1290, "free")]


def test_周日只剩一整段():
    """周日只有睡觉占用：07:30–21:30 一整段。"""
    body, got = get_segments(build_client(with_fixed=True), "2026-11-22")
    assert body["weekday"] == 7
    assert got == [(450, 1290, "free")]


def test_日期格式错误返回422():
    """2026/11/19、缺零、非法日期都要 422，且 detail 是给用户看的中文。"""
    client = build_client(with_fixed=False)
    for bad in ["2026/11/19", "2026-1-9", "2026-02-30", "20261119", "abc"]:
        response = client.get("/api/slots", params={"date": bad})
        assert response.status_code == 422, bad
        assert response.json()["detail"] == "日期要写成 2026-11-19 这样的格式"


def test_每段至少15分钟_不越界_按时间升序():
    """通用契约：minutes = end-start、≥15 分钟、不越界、升序。"""
    body, got = get_segments(build_client(with_fixed=True), "2026-11-19")
    previous_end = -1
    for item in body["items"]:
        start = to_min(item["start"])
        end = to_min(item["end"])
        assert item["minutes"] == end - start
        assert end - start >= 15
        assert 450 <= start < end <= 1290
        assert start >= previous_end
        previous_end = end


def test_全被占满时返回空列表():
    """纯函数边界：整个窗口都被占，就一段都没有（接口会返回 200 + 空数组）。"""
    assert free_segments([(450, 1290)], weekday=4) == []
