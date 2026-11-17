"""骨架自检测试：证明应用能被测试客户端启动，且两个路由都正常。

运行方式（项目根目录）：  python -m pytest -q
"""

from fastapi.testclient import TestClient

from app.main import app

# TestClient 让你不启动服务器、不打开浏览器也能"假装发请求"
client = TestClient(app)


def test_health_returns_ok() -> None:
    """/health 必须是 200，且返回体正好是 {"ok": true}。"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_index_renders_html() -> None:
    """首页必须 200 且是 HTML，说明模板目录配置正确。"""
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "骨架已启动" in response.text
