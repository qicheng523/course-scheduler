# 课表排程器（Course Scheduler）

输入真实课表 → 算出没课的空闲时间 → 把作业/复习任务自动排进空档 → 出一份"这周该干什么"的报告 → 能打卡 → 能导出文字。

**当前进度：第 1 天 · 项目骨架（v0.1.0）**。骨架只验证环境和四件套，还没有业务功能。

---

## 一、技术栈

| 层 | 选型 |
|---|---|
| 语言 | Python 3.12 |
| Web 框架 | FastAPI |
| ORM / 数据模型 | SQLModel |
| 数据库 | SQLite（单文件，零安装） |
| 模板 | Jinja2 |
| 前端交互 | HTMX |
| 样式 | Pico.css |
| 测试 | pytest |

Pico.css 和 HTMX 已经下载到 `app/static/`，**答辩现场断网也不会掉样式**。

---

## 二、目录结构

```
课表排程工作区/
├── app/
│   ├── __init__.py          包标记 + 版本号
│   ├── main.py              入口：FastAPI 实例、/health、首页
│   ├── db.py                SQLite 引擎、会话、建表
│   ├── models.py            数据表定义（共用主键基类）
│   ├── routers/             接口层（按业务分文件）
│   ├── services/            计算层（排程算法，纯函数）
│   ├── templates/           base.html / index.html
│   └── static/              pico.min.css / htmx.min.js / style.css
├── tests/
│   └── test_health.py       /health 与首页的测试
├── scripts/
│   └── check_env.py         环境自检脚本
├── docs/
│   └── 技术栈与目录说明.md
├── data/                    SQLite 数据库（自动生成 app.db）
├── requirements.txt         依赖，版本锁死
├── pytest.ini               告诉 pytest 只扫 tests/ 目录
└── README.md
```

---

## 三、跑起来（照着敲，一步一步来）

### 第 0 步：确认 Python 3.12

打开 PowerShell（Win 键 → 输入 `powershell` → 回车），输入：

```powershell
python --version
```

- 看到 `Python 3.12.x` → 跳到第 1 步
- 看到 `Python was not found` 或弹出微软商店 → 还没装 Python，去 <https://www.python.org/downloads/> 下载 **3.12 系列**的 Windows installer，
  安装时**必须勾选最下面的 `Add python.exe to PATH`**，装完关掉 PowerShell 重开，再验证一次

### 第 1 步：安装依赖（只做一次）

在项目根目录（就是能看到 `requirements.txt` 的那一层）输入：

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

- 成功标志：最后一行是 `Successfully installed ...`，且激活后命令行前面出现 `(.venv)`
- 如果 `.\.venv\Scripts\Activate.ps1` 报"禁止运行脚本"，先执行一次：
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`，输入 `Y` 回车，再重试
- 安装很慢就换国内镜像：
  `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 第 2 步：启动网站

```powershell
python -m uvicorn app.main:app --reload
```

- 成功标志：终端里出现
  `Uvicorn running on http://127.0.0.1:8000` 和 `Application startup complete.`
- **这个窗口不要关**，关了网站就停了。停止服务：按 `Ctrl + C`

### 第 3 步：打开网页验证

浏览器地址栏输入：

```
http://127.0.0.1:8000/health
```

- 看到 `{"ok":true}` → 服务正常
- 再打开 <http://127.0.0.1:8000/> → 看到首页表格，点"点我测试"按钮，下方区域出现 `{"ok":true}` → 四件套全通
- 顺带一提：<http://127.0.0.1:8000/docs> 是 FastAPI 自动生成的接口文档，答辩时可以点给老师看

---

## 四、跑测试

```powershell
python -m pytest -q
```

成功标志：`2 passed`。

## 五、环境自检（装完依赖不确定对不对时用）

```powershell
python scripts/check_env.py
```

成功标志：7 个依赖全部 `[OK]`，最后一行提示启动命令。

---

## 六、常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| `python` 打开微软商店 | 没装 Python，只有系统占位符 | 去 python.org 装 3.12，勾 `Add to PATH` |
| `Activate.ps1 无法加载` | PowerShell 执行策略限制 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: No module named 'app'` | 不在项目根目录启动 | `cd` 到有 `requirements.txt` 的那一层再启动 |
| `Address already in use` | 8000 端口被占用 | 换端口：`python -m uvicorn app.main:app --port 8001` |
| 修改代码后页面没变 | 没加 `--reload` 或窗口不是启动窗口 | 确认启动命令带 `--reload`，按 `Ctrl+C` 重启 |
| 装了依赖仍 `ModuleNotFoundError` | 终端没激活虚拟环境 | 命令行前应有 `(.venv)`，没有就重新执行第 1 步 |

---

## 七、下一步

1. 课程表：能手动加课（星期几、第几节、课程名、地点）
2. 空闲段：从课表算出每天没课的时段
3. 任务：录入作业/复习任务和截止日期
4. 排程：把任务切块排进空闲段，生成周报
5. 打卡 + 文字导出
