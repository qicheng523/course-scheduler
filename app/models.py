"""数据模型层（SQLModel）。

6 张表（字段以 docs/API.md §1 为准）：
- course       课程（只有周一到周五，每周重复）
- fixed_event  固定事件（睡觉、三餐、英语班）
- task         任务（作业、复习、刷题…）
- plan         周计划
- block        时间块（计划生成出来的"几点做什么"）
- checkin      打卡（同一天同一个任务只能打一次）

两条硬规矩：
1. 时间一律存"从 0 点开始的分钟整数"（08:00 → 480，20:35 → 1235）。
   接口上的 "HH:mm" 字符串只出现在 app/routers/courses.py，模型里不碰字符串时间。
2. plan_id / task_id 只存编号，今天先不做外键关联（任务卡允许：关联搞不定就先不关联）。

SQLModel 的特点：一个类同时是"数据库表结构"和"接口数据格式"。
"""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class BaseSQLModel(SQLModel):
    """所有业务表共用的父类：只放自增主键 id。"""

    # default=None 表示由数据库自增生成；主键不参与接口输入
    id: int | None = Field(default=None, primary_key=True)


class Course(BaseSQLModel, table=True):
    """课程：每周重复，只有周一到周五。"""

    __tablename__ = "course"

    name: str = Field(max_length=40, description="课程名")
    weekday: int = Field(ge=1, le=5, description="1=周一 … 5=周五")
    start_min: int = Field(ge=0, le=1439, description="开始时间（分钟）")
    end_min: int = Field(gt=0, le=1440, description="结束时间（分钟），必须大于开始")
    location: str | None = Field(default=None, max_length=80, description="教室，可空")
    term: str = Field(default="2026f", max_length=16, description="学期，固定 2026f")


class FixedEvent(BaseSQLModel, table=True):
    """固定事件：睡觉、三餐、英语班这类每天/每周固定占用的时间。"""

    __tablename__ = "fixed_event"

    name: str = Field(max_length=40, description="如：睡觉、午饭、英语班")
    weekday: int = Field(ge=1, le=7, description="1=周一 … 7=周日")
    start_min: int = Field(ge=0, le=1439)
    end_min: int = Field(gt=0, le=1440)
    note: str | None = Field(default=None, max_length=200)


class Task(BaseSQLModel, table=True):
    """任务：作业、复习、刷题……将来由排程算法塞进空闲时间。"""

    __tablename__ = "task"

    title: str = Field(max_length=80, description="如：线性代数第二章")
    category: str = Field(default="作业", max_length=20, description="作业 / C语言 / 项目 / 刷题 / CS50")
    duration_min: int = Field(gt=0, description="预计用时（分钟）")
    deadline: str = Field(max_length=32, description="ISO 时间，如 2026-11-20T23:59:00")
    priority: int = Field(default=2, ge=1, le=3, description="1 最高，3 最低")
    status: str = Field(default="todo", max_length=16, description="todo / scheduled / done")


class Plan(BaseSQLModel, table=True):
    """一份周计划（D6 生成）。"""

    __tablename__ = "plan"

    week_start: str = Field(max_length=10, description="那周的周一，如 2026-11-16")
    created_at: str = Field(max_length=32, description="生成时间（ISO 字符串）")


class Block(BaseSQLModel, table=True):
    """时间块：某个计划里"某天几点到几点做什么"。"""

    __tablename__ = "block"

    plan_id: int = Field(description="属于哪份计划（先只存编号，不做外键）")
    task_id: int | None = Field(default=None, description="空 = 这是课或固定事件，不是任务")
    date: str = Field(max_length=10, description="如 2026-11-18")
    start_min: int = Field(ge=0, le=1439)
    end_min: int = Field(gt=0, le=1440)
    kind: str = Field(max_length=16, description="course / fixed / task / free")


class Checkin(BaseSQLModel, table=True):
    """打卡：同一天同一个任务只能打一次（幂等）。"""

    __tablename__ = "checkin"
    # (task_id, date) 唯一：重复打卡不会多出一条记录，也不会重复计数
    __table_args__ = (UniqueConstraint("task_id", "date", name="uq_checkin_task_date"),)

    task_id: int = Field(description="打的是哪个任务")
    date: str = Field(max_length=10, description="如 2026-11-18")
    done_at: str = Field(max_length=32, description="打卡时间（ISO 字符串）")
    note: str | None = Field(default=None, max_length=200)
