# 给三个人的说明书：文件怎么分、GitHub 怎么用

> 这份是写给 A、B、C 三个人一起看的，不需要任何基础。
> 看完你应该能回答三个问题：**我管哪几个文件？每天怎么交？文件传到哪儿？**
> 配套：`TEAM.md`（定了的事）、`docs/API.md`（前后端的"点菜单"）。

> ✅ **2026-11-18 更新：仓库名已改成 `course-scheduler`。** 下文出现的 `coruse-scheduler` 都是改名前的老名字，指的是同一个仓库。
> 另外：§8 那段"今晚 C 把骨架传上去"的操作**已经全部做完**，只当历史看，不要再照着敲一遍。

---

## 开场：可以直接发群里的一段话

> 我们的代码放在一个共享的地方（GitHub）。**不要在微信里传文件**——三个人各存一份，三天后就合不起来了。
> 规矩三条：① 只改自己那一格的文件；② 要改别人的先说一句；③ 每天收工前交一次（Push）。
> 每天的动作就三个词：**拉（Pull）→ 改 → 交（Commit & Push）**。

---

# 第一部分：文件怎么分

## 1. 现在的项目长这样

```text
课表排程工作区/  (= 仓库根目录)
│
├── app/                    ← 网站本体
│   ├── main.py             ← 大门：程序从这里启动（C）
│   ├── db.py               ← 怎么连数据库（C）
│   ├── models.py           ← 数据表长什么样（C）
│   ├── routers/            ← 各种"接口"，网页问后台要数据的地方（C）
│   ├── services/           ← 算法：算空档、排时间（C）
│   ├── templates/          ← 网页长什么样（A）
│   └── static/             ← 样式、按钮颜色、小图标（A）
│
├── tests/                  ← 自动检查，跑一下就知道有没有改坏（C）
├── scripts/                ← 一次性小工具：灌数据、重置数据库（B）
├── data/                   ← 数据文件（B）
│   ├── seed-courses.txt    ← 19 条真实课表（9 节模型），灌库用
│   └── app.db              ← 数据库本体（程序自动生成，不传）
├── docs/                   ← 文档（三人按需）
│   ├── API.md              ← 前后端契约（C 维护）
│   └── 技术栈与目录说明.md
├── test-data/              ← B 传的课表测试数据（导入试验用）
├── README.md               ← 别人怎么把项目跑起来（B）
├── TEAM.md                 ← 分工与规矩（已定，别改）
├── requirements.txt        ← 依赖清单（谁都不许乱改）
└── pytest.ini              ← 测试配置（谁都不许乱改）
```

**一句话理解**：`app/` 里，**routers + services + models 是后台（算账的）**，**templates + static 是前台（看得见的）**，其余都是配套。

## 2. 谁管哪一格（贴在群里，别改）

| 谁 | 管这些 | 说人话 | 接下来要建的 |
|---|---|---|---|
| **C** | `app/main.py`、`app/db.py`、`app/models.py`、`app/routers/`、`app/services/`、`tests/`、`docs/API.md` | 后台：数据存哪、怎么算、怎么排时间 | `routers/courses.py`、`tests/test_api_courses.py` |
| **A** | `app/templates/`、`app/static/`、`docs/UI.md`、`docs/wireframes/` | 前台：页面长什么样、按钮在哪、手机上挤不挤 | `templates/courses.html` |
| **B** | `scripts/`、`data/`、`.github/`、`README.md`、`docs/SETUP.md`、`docs/DEPLOY.md` | 数据与上线：课表怎么灌进去、怎么放上网 | `scripts/seed.py`、`scripts/reset_db.py` |

**`requirements.txt`、`pytest.ini`、`.gitignore`、`TEAM.md` 是三个人共用的地基**——改了所有人的电脑都可能跑不起来，动之前先在群里说。

## 3. 三条规矩（违反一定出事）

1. **只改自己那一格的文件。** 两个人同时改同一个文件，GitHub 会不知道该留谁的那份，你们两个都得重做。
2. **要改别人的文件，先在群里说一句**，等对方回"可以"再动。
3. **每天收工前一定交（Push）。** 不交 = 你的活不存在，别人拉下来看不到。

## 4. 三个人怎么配合（不是各写各的）

- **C 先定"数据长什么样"**（课程有哪些字段：名字、星期几、几点到几点、地点），写进 `docs/API.md`。
- **A 不等 C 写完**：拿 `docs/API.md` 里的 JSON 示例，用假数据把页面做出来；C 的接口好了，改一行地址就接上真的。
- **B 的 seed 数据必须和 `docs/API.md` 的字段名一模一样**，否则插不进去。

> 所以：**A 和 B 都看 `docs/API.md`，不看 C 的代码。** 这张清单就是我们三个人的合同。

## 5. 每天的具体动作（照做）

| 时间 | 做什么 | 大概多久 |
|---|---|---|
| 开始干活前 | 打开 GitHub Desktop → 点 **Pull origin**（把别人昨天交的拉下来） | 10 秒 |
| 干活中 | 只改自己的文件；AI 让你改别人的文件时，先说"这个不归我管" | — |
| 收工前 | GitHub Desktop → 左下角写一句说明（例：`C: 加了课程表`）→ **Commit to main** → **Push origin** | 1 分钟 |
| 收工后 | 群里发一句：今天交了 + 截图 | 30 秒 |

---

# 第二部分：GitHub 怎么用

## 6. 为什么不用微信传文件

微信传文件 = 三个人各有一份，改完再传回来，**文件名会变成"课程表(1)(2)(最终)(最终真的).py"**，谁也不知道哪份是最新的。

GitHub 解决三件事：

- **只有一份**，所有人看同一个；
- **有记录**，谁在什么时候改了什么，一清二楚；
- **能反悔**，改坏了可以退回到昨天的版本。

**所以"把文件发给别人"这件事不存在**：文件就在仓库里，他 Pull 一下就有了。群里只发三样：截图、commit 链接、`docs/API.md` 的改动说明。

## 7. 哪些文件要传，哪些绝对不能传

| 文件 / 文件夹 | 传不传 | 为什么 |
|---|---|---|
| `app/`、`tests/`、`scripts/`、`docs/`、`data/seed-courses.txt`、`test-data/` | ✅ 传 | 代码、文档、种子数据 |
| `README.md`、`TEAM.md`、`requirements.txt`、`pytest.ini`、`.gitignore` | ✅ 传 | 别人靠它跑起来 |
| **`.venv/`** | ❌ **绝对不传** | 你电脑上的 Python 环境，几百 MB，传上去 GitHub 会拒收 |
| **`__pycache__/`、`.pytest_cache/`** | ❌ 不传 | 运行时自动生成的缓存，没用 |
| **`data/app.db`** | ❌ 不传 | 数据库文件，启动会自动重建；传上去会覆盖别人的数据 |
| `.env`、密码、密钥 | ❌ 永远不传 | 传了等于把密码公开 |
| 团队内部规划（`团队开局手册-今晚就用.md`、`冲刺日程-到11-29.md`、`今晚*.md`） | ❌ 不传 | 群里发过，属于内部作战文档，不放进公开仓库 |

**怎么做到"自动不传"**：根目录的 `.gitignore` 已经列好了名单，GitHub Desktop 会自动跳过。**不要删它、不要改它**（要改先问 C）。

> 判断方法：GitHub Desktop 左边列出的文件应该只有**几十个**。如果出现几千个、还有 `.venv` 字样，说明 `.gitignore` 没生效，**先别 Commit**，群里喊 C。

## 8. 【今晚 · C 做】把骨架传上去（照着做）

### 8.0 先解释你看到的"空仓库"

你这步做错的地方不是操作，是**选错了按钮**：

- 你在 GitHub Desktop 点的是 **Create new repository**（新建空仓库）。它只在 `D:\dsh-workspaces\course-scheduler` 建了一个只有 `.git` 和 `.gitattributes` 的空壳子，**不会把别处的项目文件搬进来**——所以你看不到文件。
- 真正的项目文件在 **`D:\dsh-workspaces\课表排程工作区`**。
- 更麻烦的是：GitHub 上你真正的仓库叫 **`coruse-scheduler`**（名字少了一个 `u`），而你本地这个空仓库叫 `course-scheduler`。**如果你在 GitHub Desktop 点 Publish，会再建一个同名的新仓库，变成两个仓库，后面全乱。**
- 所以：**今晚不要点 Publish。** 用下面的命令把现在这个文件夹接到已有的 `coruse-scheduler` 上。

> ✅ **11-17 23:25 更新：fetch / 合并 / 本地提交这三步，AI 已经在这台电脑上跑完了**（`git log` 现在有 4 条提交：B 的 3 条 + 你的骨架 1 条）。
> **你不用再跑 §8.2 里的 fetch / reset / commit**，现在只差最后一步：**把本地提交 push 到 GitHub**——跑本节最后一条 `git push`，或用 §8.4 的 GitHub Desktop 方法。
> 之前 git 连不上 GitHub 的原因也修好了：你的电脑开着系统代理（`127.0.0.1:7897`），但 git 默认不走系统代理；我已经在这个仓库里配置好了代理，命令能直接通。

### 8.1 先清掉那个空仓库（1 分钟）

1. 打开 GitHub Desktop，左上角 **Current Repository** 里找到 `course-scheduler`。
2. 右键 → **Remove**（只从列表移除，别点 Delete）。
3. 资源管理器里把 `D:\dsh-workspaces\course-scheduler` 这个文件夹删掉——里面只有 `.git` 和 `.gitattributes`，**没有你的任何文件**。（不确定就先留着，不删也不影响。）

### 8.2 打开 PowerShell，按顺序跑（5 分钟）

> ⚠️ **下面的 fetch / reset / checkout / commit 已经执行完，不要再跑一遍**（重复 reset 会把你的提交挪走）。直接跳到**最后一条 `git push`**。

Win 键 → 输入 `powershell` → 回车。**一行一行复制、回车，等上一行跑完再贴下一行。**

```powershell
cd "D:\dsh-workspaces\课表排程工作区"
```

```powershell
git fetch origin
```

> 这一步只是"把 GitHub 上已有的东西取到本地"，**不会改你的任何文件**。
> 如果弹出登录窗口：选浏览器登录，用你的 GitHub 账号（`qicheng523`）授权一次；**GitHub 不能用密码，别在密码框里硬试**。

```powershell
git log --oneline origin/main
```

**应该正好 3 行**（B 传的）：

```text
eb8390a 补充 11/17 日总结
e5a1358 添加课表测试数据与格式说明
0bffe70 Add README.md
```

> 如果**多于 3 行**：停下，把输出截图发群里——说明 B 又传了新东西，要先确认没漏。

```powershell
git reset --soft origin/main
git checkout origin/main -- test-data
git status --short
```

> 第二条是把 B 传的 `test-data/` 取回来（不会覆盖你的骨架）。
> 第三条是"检查一下"：你应该看到**很多以 `A ` 开头的行**（新增的文件）和**一行 `M  README.md`**。
> **只要没有以 `D ` 开头的行，就继续。** 有 `D ` 就停下发群里。

```powershell
git add -A
git commit -m "C: 项目骨架 v0.1.0 + 合并 B 的课表测试数据"
```

```powershell
git push -u origin main
```

**成功的标志**：最后几行里有

```text
branch 'main' set up to track 'origin/main'.
...
To https://github.com/qicheng523/coruse-scheduler.git
 * [new branch]      main -> main
```

（第一次 push 可能弹一次浏览器登录，同上。）

> **如果最后一步 push 卡在登录/报认证错误**：前面几条（跑到 `git commit` 为止）都已经成功的话，直接打开 GitHub Desktop → `File` → `Add local repository` → 选 `D:\dsh-workspaces\课表排程工作区` → 点右上角 **Push origin**。GitHub Desktop 已经登录过，不会再问一次。
>
> **如果连 `git fetch origin` 都报网络错**：同样先在 GitHub Desktop 里 Add local repository → 点 **Fetch origin**，成功后再回 PowerShell，从 `git log --oneline origin/main` 那一步继续。

### 8.3 验证（30 秒）

浏览器打开 <https://github.com/qicheng523/coruse-scheduler>，应该能看到：

- 文件列表里有 `app/`、`docs/`、`tests/`、`TEAM.md`、`test-data/`；
- 顶部 commit 记录里，最新一条是你写的 `C: 项目骨架 v0.1.0 + 合并 B 的课表测试数据`；
- **没有** `.venv`、`__pycache__`、`app.db`。

### 8.4 之后在 GitHub Desktop 里怎么用

1. GitHub Desktop → `File` → **Add local repository**。
2. 选 **`D:\dsh-workspaces\课表排程工作区`** → 点 Add。
3. 它会直接显示历史记录（4 条 commit），不会再让你 Publish。
4. 以后每天就用 **Pull origin / Commit to main / Push origin** 三个按钮，不用再敲命令。

### 8.5 两个可选的小修（建议做，各 10 秒）

- **仓库名拼错了**：GitHub 网页 → 仓库 → `Settings` → `Rename` → 改成 `course-scheduler`。
  改名后旧链接会自动跳转；你本地的 `origin` 也能继续用（不放心就下次 push 前跑一次 `git remote set-url origin https://github.com/qicheng523/course-scheduler.git`）。
- **仓库现在是 Public（公开）**：`Settings` → 最下面 `Change visibility` → `Make private`。答辩要给老师看链接时再改回来。

## 9. A 和 B 第一次：把项目下载到自己电脑（5 分钟）

**前提**：C 已经把你加进仓库，并且**你在 GitHub 上点过接受邀请**（邮箱里那封 "You've been invited" 的邮件）。

1. 装 **GitHub Desktop**，登录自己的 GitHub 账号。
2. 点 `File` → `Clone repository`。
3. 在列表里选 `qicheng523/coruse-scheduler`（找不到就点 URL 标签，粘 `https://github.com/qicheng523/coruse-scheduler.git`）。
4. Local path 选一个你找得到的地方（比如 `D:\projects\course-scheduler`）。
5. 点 **Clone**。

下载完，在文件夹里看到 `app/`、`README.md`、`TEAM.md`、`docs/API.md` 就成功了。

> **不要**在网页上点 "Download ZIP"。那样下载的是一份死文件，你改完传不回去，还得重来。
> **不要**用 GitHub Desktop 的 "Create new repository"——那就是今晚 C 踩的坑。

## 10. 之后每天：三个动作

```text
① 拉    打开 GitHub Desktop → 点 Pull origin
② 改    只改自己的文件（AI 帮你写，你负责保存到对的路径）
③ 交    左下角写一句说明 → Commit to main → Push origin
```

**说明怎么写**（一句话就够，写清楚"谁 + 干了啥"）：

```text
C: 加了 6 张表和课程接口
A: 课程页能加课了
B: seed 脚本灌进 19 条真实课表
```

## 11. 出错了怎么办（对照下表）

| 屏幕上出现 | 什么意思 | 怎么办 |
|---|---|---|
| `No local changes` / 没有变化 | 你还没改文件，或改的不是这个文件夹 | 确认文件保存到了项目文件夹里 |
| `Push rejected` / 推送被拒绝 | 别人比你先交了 | 先点 **Pull origin**，再点 **Push origin**；还不行就在群里喊 |
| `conflict` / 冲突 | 你和别人改了**同一行** | **停手，别乱点**。群里说"谁的 xxx 文件冲突了"，留一个人的版本，另一人重做 |
| `Authentication failed` | 没登录或登录过期 | GitHub Desktop → File → Options → Accounts → 重新登录 |
| `Failed to connect to github.com:443` / `Could not connect to server` | git 没走代理，直连 GitHub 超时 | 确认代理软件开着（本机是 Clash，端口 `7897`）；本仓库已经配置 `http.proxy`，如果代理端口改了：`git config http.proxy http://127.0.0.1:新端口`；以后不开代理时用 `git config --unset http.proxy` 去掉 |
| `Could not resolve host` | DNS 被污染/网络断开 | 打开代理软件，或换手机热点再试 |
| `fatal: not a git repository` | 当前文件夹不是仓库根 | 先 `cd "D:\dsh-workspaces\课表排程工作区"` 再跑命令 |
| `error: src refspec main does not match any` | 还没做第一次 commit | 先跑 `git add -A` 和 `git commit -m "..."` |
| 左边突然出现几千个文件 | `.gitignore` 没生效 | **先别 Commit**，群里喊 C |
| 红色 `failed` / 看不懂的英文 | 报错 | 把**整段**截图发群里，让 AI 解释，不要自己猜 |

---

# 第三部分：三个最常问的问题

## 12. 要做账号 / 登录吗？设置界面怎么放？

**结论：不做。** 理由和答辩话术见 `TEAM.md` §4.1，一句话版：

> 14 天里没有这项；做登录最少要 2–2.5 天，得砍掉排程或报告；答辩 5 步里没有登录，多一步多一次翻车；个人工具，数据在本地，不做账号反而更安全。

**那"设置页"放什么**（没有账号，所以没有"账号"这一块）：

1. **数据**：重新导入课表、重置为演示数据（二次确认）、导出全部数据；
2. **显示**：学期名、当前周次、九节时间表（只读）；
3. **关于**：版本号、技术栈、数据库文件位置。

不做：密码、头像、通知、主题切换、多语言。这页是 P1，D8 之后有余力再做，不做也不影响答辩。

## 13. 什么时候能让"别人"用？

| 时间 | 到什么程度 | 谁能用 |
|---|---|---|
| D2 今晚（11-17） | 首页能打开、能加课 | 只有 C 自己的电脑（`127.0.0.1`） |
| D6（11-21 周六） | 自动排程第一次跑通 | 你演示给 1 个同学看（还在你电脑上） |
| D9（11-24 周二） | 统计 + 2 个用户测试 | 同学能真正试用（要装 Python，或来你电脑） |
| **D10（11-25 周三）** | **首次部署到公网** | **打开链接就能用——这才是"其他人能用"** |
| D13（11-28 周六） | 彩排 + 离线兜底 | 答辩现场 |
| D14（11-29 周日） | 提交 + 现场演示 | 老师 |

> 如果 D10 部署没搞定，按砍单顺序先砍"公网部署"：**演示改成来你电脑上点**，不影响及格。
> 注意："别人能用"不等于"多人共用"——我们没有账号，所有数据是同一份，演示时用你自己的数据。

## 14. 每天 30 秒自检

- [ ] 浏览器打开仓库，最新一次提交是**今天**的
- [ ] 别人 Pull 下来，能跑起来（至少能打开首页）
- [ ] 没有把 `.venv`、`data/app.db`、团队内部规划文档传上去

---

## 附：一句话记住

> **一份文件放在网上，三个人各改自己那一格，每天收工前交一次。**
> 能做到这一句，这个项目就不会因为"文件对不上"而崩。

---

*遇到表里没有的问题，把屏幕整段截图发群里，不要自己乱点。*
