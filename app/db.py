"""数据库连接层：SQLite + SQLModel。

这个文件只做三件事：
1. 保证 data/ 目录存在（数据库文件 data/app.db 就放在里面）
2. 创建数据库引擎（engine）和会话（Session）
3. 提供 create_db_and_tables()，应用启动时按 models.py 的定义建表
"""

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# 项目根目录 = app 目录的上一级。用绝对路径的好处：
# 不管你在哪个文件夹里执行 uvicorn，data/app.db 永远指向同一个文件。
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"

# SQLite 不会自动创建文件夹，所以建引擎之前必须先建目录
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 数据库地址：三个斜杠表示"本地文件"，后面接绝对路径
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# check_same_thread=False：FastAPI 处理请求时可能换线程，
# SQLite 默认禁止跨线程使用同一连接，加上这个参数才不会报错。
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    """按 models.py 里已注册的模型建表；表已存在则自动跳过。"""
    # 必须先导入 models 模块，SQLModel 才知道有哪些表要建
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI 依赖注入用：每个请求拿一个数据库会话，请求结束自动关闭。"""
    with Session(engine) as session:
        yield session
