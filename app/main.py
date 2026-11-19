"""应用入口：创建 FastAPI 实例，挂模板、静态文件，暴露路由。

今天只有两个路由：
- GET /health  健康检查，返回 {"ok": true}，供测试脚本和部署探针使用
- GET /        首页，只做技术栈自检，不含任何业务功能
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import __version__
from app.db import DB_PATH, create_db_and_tables
from app.routers import courses, plan

# 各个目录的绝对路径：一律用绝对路径，避免"换个目录启动就找不到模板"的坑
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时执行一次：按模型定义建表。"""
    create_db_and_tables()
    yield


# title / version 会显示在自动生成的接口文档 /docs 里
app = FastAPI(title="课表排程器", version=__version__, lifespan=lifespan)

# 把 /static/xxx 的请求映射到 app/static/ 目录下的真实文件
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 模板引擎：渲染 app/templates/ 下的 .html 文件
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 把课程接口挂上来：/api/courses 的增删改查都在 app/routers/courses.py 里
app.include_router(courses.router)

# 把空闲段接口挂上来：/api/slots 在 app/routers/plan.py 里
app.include_router(plan.router)


@app.get("/health")
def health() -> dict[str, bool]:
    """健康检查：返回固定的 {"ok": true}。

    这是最省事的"服务是否活着"判断方式：
    只要这个接口 200 且 ok 为 true，就说明 Web 服务、路由注册都正常。
    """
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """首页：渲染骨架自检页，证明 Jinja2 模板链路可用。"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "version": __version__,
            "db_path": str(DB_PATH),
        },
    )

@app.get("/courses", response_class=HTMLResponse)
def courses_page(request: Request):
    """课程页：模板由 A 负责，页面数据由 A 用 HTMX 调 /api/courses 拿。"""
    return templates.TemplateResponse(
        request=request,
        name="courses.html",
        context={"version": __version__, "db_path": str(DB_PATH), "courses": []},
    )