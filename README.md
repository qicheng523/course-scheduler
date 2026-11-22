# 课表排程器（Course Scheduler）

把真实课表输进去 → 系统算出每天哪些时间是空的 → 把作业/复习任务自动排进这些空档 → 出一份"这周该干什么"的报告 → 能打卡 → 能导出成文字。

**当前状态（2026-11-22）**：功能已经跑通，`pytest` 47 个测试全绿。
课程管理、空闲段计算、自动排程、周报告、打卡、周统计、Markdown 导出都能用。

> 只想赶紧看到网页？跳到 §3，照着敲 4 条命令，5 分钟能开起来。

---

## 1 它解决什么问题

大学生知道"这周有作业"，但算不清"哪个晚上有空、该先写哪个"。这个工具把这件事自动化：

- 课表是**每周重复**的（周一到周五，19 个课次）；
- 睡觉、三餐、英语班是**固定占用**；
- 剩下的时间按 **15 分钟** 对齐，切成一段段空闲；
- 任务按**优先级 + 截止时间**塞进空档，排不下的告诉你为什么；
- 晚上 **19:00–21:00 是晚自习**，属于"可以学习但不是普通空闲"的特殊时段：前后各留 10 分钟走路，任务块不许跨进跨出。

---

## 2 你需要什么

| 需要 | 说明 |
|---|---|
| Windows 10/11（macOS / Linux 也能跑，命令里把 `\` 换成 `/`） | 下面所有命令都以 Windows 为例 |
| Python **3.12** | 装的时候**必须勾选 `Add python.exe to PATH`** |
| 一个浏览器 | Edge / Chrome 都行 |
| 约 200 MB 磁盘 | 依赖 + 数据库 |

检查 Python 装没装：打开终端，输入 `python --version`，看到 `Python 3.12.x` 就行。

---

## 3 第一次跑起来（Windows，5 分钟）

### 3.1 打开终端，并进到项目文件夹

**最省事的打开方式**：用文件资源管理器打开项目文件夹（能看到 `README.md` 的这一层），
点一下窗口上方的**地址栏**，把里面的路径删掉，输入 `powershell`，回车 —— 终端会直接开在这个文件夹里。

> 也可以用 Win 键 → 输入 `powershell` → 回车，然后手动进入文件夹：
> ```powershell
> cd "D:\dsh-workspaces\课表排程工作区"
> ```

**确认站对了地方**（这一步最容易出错）：

```powershell
Get-ChildItem requirements.txt
```

看到列出 `requirements.txt` 就是对的。如果报"找不到路径"，说明你不在项目文件夹里，回到上一步。

### 3.2 创建虚拟环境 + 装依赖（只做一次）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- 第一行会建一个 `.venv` 文件夹（几百 MB，**不要提交到 git**，`.gitignore` 已经排除）。
- 第二行成功标志：最后出现 `Successfully installed ...`。
- 装得慢就加国内镜像：
  `.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
- **不需要"激活"虚拟环境**。下面所有命令都写成 `.\.venv\Scripts\python.exe -m ...`，直接指定用哪个 Python，省掉 `Activate.ps1` 那一堆 PowerShell 执行策略的坑。

### 3.3 灌演示数据（只做一次）

```powershell
.\.venv\Scripts\python.exe scripts\reset_db.py --yes
.\.venv\Scripts\python.exe scripts\seed.py
```

- 第一条：删掉旧的 `data/app.db`，建一个空库（**会清空已有数据**，演示前也用它）。
- 第二条：灌 **19 门课 + 35 条固定事件 + 5 条任务**。
- 成功标志：最后几行出现 `写入：课程 19 条、固定事件 35 条`。

> 3.3 之前如果网站正在运行，先按 `Ctrl + C` 停掉再重置（Windows 上删正在被占用的数据库文件会失败）。

### 3.4 启动网站

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

成功标志，终端里出现这两行：

```
Uvicorn running on http://127.0.0.1:8000  (Press CTRL+C to quit)
Application startup complete.
```

- **这个窗口不能关**，关了网站就停了。
- 停止服务：在窗口里按 `Ctrl + C`。
- `--reload` = 改了代码自动重启（开发时用；正式演示可以不加）。

### 3.5 打开网站

浏览器地址栏输入（注意是 `http://`，不是 `https://`）：

```
http://127.0.0.1:8000/
```

打开后应该看到：**本周报告**（几个数字）+ **今天做什么** + **本周安排**。

- 第一次打开如果显示 **"这一周还没有生成计划"**，点页面上的 **「生成本周计划」** 按钮即可。
- 想看课程列表：<http://127.0.0.1:8000/courses>
- 计划页（和首页是同一套内容，导航里的"计划"也到这里）：<http://127.0.0.1:8000/plan>
- 服务是否活着：<http://127.0.0.1:8000/health> → `{"ok":true}`

> `http://127.0.0.1:8000` 里的 `127.0.0.1` 意思是"我自己这台电脑"。**别人电脑打不开**，这是本地工具，不是网站。

---

## 4 第二次以后怎么启动（只要 3 步）

```powershell
cd "D:\dsh-workspaces\课表排程工作区"          # ① 进项目文件夹
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload   # ② 启动
```

③ 浏览器打开 `http://127.0.0.1:8000/`。

依赖和数据都还在，**不用**再装、也不用再灌数据。

---

## 5 三个页面 / 演示路线

| 地址 | 页面 | 能做什么 |
|---|---|---|
| `/` | 首页 = 计划页 | 本周报告（已排/已完成/未排/总时长）、今天做什么、本周安排、打卡、导出周报 |
| `/courses` | 课程表 | 查看 19 门课、加课、删课；时间冲突会显示中文提示 |
| `/plan` | 计划页 | 和首页同一套内容（导航里的"计划"） |

**5 分钟演示路线**（按顺序点）：

1. 打开 `/` → 看到本周报告的数字；
2. 往下滚 → "今天做什么"；
3. 点某一行任务的 **「打卡」** → 该行变灰 + ✅，刷新页面还在；
4. 看 **「本周统计」** 的 4 个数字，和 `/api/plan/...` 里的对得上；
5. 点 **「导出周报」** → 下载 `.md`，中文正常。

完整演示脚本见 [`docs/DEMO.md`](docs/DEMO.md)。

---

## 6 数据：在哪、怎么重置、怎么备份

| 想干什么 | 怎么做 |
|---|---|
| 数据库在哪 | `data/app.db`（一个 SQLite 文件，**不进 git**） |
| 重置成演示数据 | 停服务 → `.\.venv\Scripts\python.exe scripts\reset_db.py --yes` → `.\.venv\Scripts\python.exe scripts\seed.py` |
| 备份 | 把 `data/app.db` 复制一份改名存起来 |
| 改真实课表 | 改 `data/seed-courses.txt`（一行一节课，格式：`星期 节次 课程名 地点 老师`），再重跑 `seed.py` |
| 清掉打卡记录 | 重置 + 重灌（或者用 SQLite 工具删 `checkin` 表数据） |

---

## 7 跑测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

成功标志：**`47 passed`**，0 failed。
测试全部使用内存数据库，**不会动 `data/app.db`**，可以随便跑。

环境自检（依赖装没装全）：

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

---

## 8 常见问题

| 屏幕上出现 | 原因 | 解决 |
|---|---|---|
| `python` 打开微软商店 | 没装 Python，只有系统占位符 | 去 python.org 装 3.12，勾 `Add python.exe to PATH` |
| `ModuleNotFoundError: No module named 'app'` | 不在项目根目录启动 | `cd` 到能看到 `requirements.txt` 的那一层再启动 |
| `Address already in use` / 端口被占用 | 8000 已有程序在跑（可能是上一次没关） | 换端口：`--port 8001`，浏览器也要改成 `http://127.0.0.1:8001/`；或关掉旧终端 |
| `TemplateNotFound: xxx.html` | 模板文件没建好 / 路径不对 | 确认 `app/templates/` 下有这个文件 |
| 页面一片空白，或所有按钮都没反应 | 静态文件（`app/static/`）没加载 | 按 `F12` 看 Console 的红色报错，整段截图 |
| 中文变乱码 | 终端编码不是 UTF-8 | 先执行 `chcp 65001` 再跑命令（不影响数据库） |
| 改了数据库，页面没变 | 浏览器缓存 | `Ctrl + F5` 强刷 |
| `Failed to connect to github.com:443` | git 没走代理，直连超时 | 确认代理软件开着（本机 Clash 端口 `7897`）；或临时 `git config --unset http.proxy` |
| 装了依赖仍然报缺包 | 用的不是 `.venv` 里的 Python | 所有命令都用 `.\.venv\Scripts\python.exe -m ...` 开头 |

---

## 9 目录结构

```
课表排程工作区/
├── app/
│   ├── main.py            入口：FastAPI 实例、页面路由（/ /courses /plan /health）
│   ├── db.py              SQLite 引擎、会话、建表
│   ├── models.py          6 张表：course / fixed_event / task / plan / block / checkin
│   ├── routers/
│   │   ├── courses.py     课程增删改查（/api/courses）
│   │   └── plan.py        空闲段 / 生成计划 / 打卡 / 统计 / 导出
│   ├── services/
│   │   ├── slots.py       空闲段算法（纯函数，含晚自习四切点）
│   │   └── scheduler.py   排程算法（切块 + 贪心放置）
│   ├── templates/         base / index / courses / plan / tasks
│   └── static/            pico.min.css / htmx.min.js / style.css / plan.js
├── tests/                 test_health / test_courses / test_slots / test_plan
├── scripts/               seed.py（灌数据）/ reset_db.py（重置）/ check_env.py（自检）
├── data/
│   ├── seed-courses.txt   19 条真实课表（唯一数据源）
│   └── app.db             SQLite 数据库（自动生成，不进 git）
├── docs/
│   ├── API.md             前后端字段与接口的"合同"（最重要的一份文档）
│   ├── DEMO.md            5 分钟演示脚本
│   ├── DEPLOY.md          怎么放到公网
│   └── 技术栈与目录说明.md
├── .github/workflows/ci.yml   每次 push 自动跑测试 + 数据冒烟
├── requirements.txt       依赖（版本锁死，别乱改）
├── pytest.ini             测试配置
└── README.md
```

---

## 10 技术栈（为什么是这些）

| 层 | 选型 | 为什么 |
|---|---|---|
| 语言 | Python 3.12 | 三个人只学过 C，Python 上手最快 |
| Web 框架 | FastAPI | 接口写完自动有 `/docs` 文档，报错信息清楚 |
| 数据模型 | SQLModel | 一个类同时是"表结构"和"接口格式"，少写一半代码 |
| 数据库 | SQLite | 单文件、零安装，拷走 `app.db` 就是全部数据 |
| 模板 | Jinja2 | 服务端渲染，不学前端框架也能出页面 |
| 交互 | HTMX + 原生 fetch | 不用 npm / React，按钮点了能局部刷新 |
| 样式 | Pico.css | 别人写好的 CSS，拷进 `static/` 就能用 |
| 测试 | pytest | 一条命令跑完全部测试，改坏了立刻知道 |

**Pico.css、HTMX 都已经下载到 `app/static/`，现场断网也不会掉样式。**

---

## 11 文档索引

| 文档 | 给谁看 | 内容 |
|---|---|---|
| [`docs/API.md`](docs/API.md) | 前后端都看 | 6 张表的字段、10+ 个接口的请求/响应格式（**改字段先改这里**） |
| [`docs/DEMO.md`](docs/DEMO.md) | 演示的人 | 5 分钟演示脚本、每步说什么 |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | 部署的人 | 怎么从零跑起来、怎么放上公网 |
| [`docs/技术栈与目录说明.md`](docs/技术栈与目录说明.md) | 新手 | 每个文件是干什么的 |
| [`TEAM.md`](TEAM.md) | 团队内部 | 分工、已经定了的事（不做登录等） |
