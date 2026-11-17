"""数据模型层（SQLModel）。

今天只定义一张"所有表共用的基类"，提供自增主键 id。
明天开始，课程表 / 任务表 / 计划表 / 打卡表 都继承 BaseSQLModel，
每张表就自动拥有 id，不用重复写字段定义。

SQLModel 的特点：一个类同时是"数据库表结构"和"接口数据格式"，
写一次类，建表和 JSON 序列化都自动完成。
"""

from sqlmodel import Field, SQLModel


class BaseSQLModel(SQLModel):
    """所有业务表共用的父类，只放公共字段。"""

    # default=None 表示由数据库自增生成；主键不参与 API 输入
    id: int | None = Field(default=None, primary_key=True)
