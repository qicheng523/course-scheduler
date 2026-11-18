# GitHub Desktop 每日操作手册（零基础版）

> 适用：3 人课表排程小组（A=前端/QA/演示，B=数据/部署/文档，C=后端/算法/集成）
> 版本 v1.0 · 2026-11-18 · 维护：全组共管（改之前群里说一句）
> 用法：第 0–1 节 3 分钟看完；第一次配置按第 2 节做一次（约 20 分钟）；之后每天只做第 3–5 节。

---

## 0. 一分钟搞懂：这些词到底在说什么

把 **GitHub 想成一个云端的"保险柜"**，里面放着我们三个人的项目。**git 是保险柜的"存档系统"**：每次存档都会记下"谁、什么时候、改了哪几个文件、改了什么"。

| 动作 | 英文 | 一句话解释 | 比喻 |
|---|---|---|---|
| 克隆 | Clone | 第一次把整个项目从云端搬到你的电脑 | 把保险柜整个复制一份回家 |
| 拉取 | Pull | 把队友新上传的东西下载到你电脑 | 把家里那份更新成最新 |
| 提交 | Commit | 在你电脑上给当前版本拍一张快照（**还没上传**） | 游戏存档 |
| 推送 | Push | 把快照上传到云端，队友才能看到 | 存档同步到云 |
| 检查更新 | Fetch | 只问一句"云端有没有新东西"，**不动你的文件** | 刷一下"有没有新消息" |

**最重要的一句话**：`Commit` 只在你自己电脑上，**队友看不到**；一定要再点 `Push origin`，队友才拿得到。

**为什么不用微信传文件**：微信传的 .py 文件会互相覆盖、没有历史、不知道谁改了什么。项目代码只走 git（这条是队规）。

---

## 1. 每天 3 分钟版（把这一格贴在屏幕边）

**开工**
1. 打开 **GitHub Desktop**，确认左上角仓库是 `course-scheduler`。
2. 点 **Fetch origin**；如果它变成 **Pull origin**，就点它（这就是"下载最新文件"）。

**干活**
3. 只改**自己负责**的文件（分工表见 §5），用 **VS Code** 改，不要在 Desktop 里改。

**收工**
4. 点 **Changes**，**只勾选自己改的文件**。
5. 点开每个文件看一眼 diff（绿色是加的，红色是删的）。
6. 在 **Summary** 里写 `代号: 干了啥`，例如 `A: 课程页能加课了`。
7. 点 **Commit to main**，再点 **Push origin**。
8. 打开网页版仓库刷新一下，**看到自己那条提交 = 成功**。

**红线（一条都不能破）**
- 不点 `Discard changes`（未提交的改动会**永久消失**）。
- 不做 force push（会覆盖队友）。
- 看到 `conflicts`（冲突）**立刻停手**，截图发群 @C。
- 代码不通过微信传。
- 不提交 `.venv/`、`data/app.db`、`.env`、真实姓名/学号。

---

## 2. 第一次配置（每人只做一次，约 20 分钟）

### 2.1 装 GitHub Desktop
- 官网：**https://desktop.github.com**（Windows 版自动识别）。
- 只从官网下，别从网盘/软件管家下。

### 2.2 登录自己的 GitHub 账号
1. 打开 GitHub Desktop → 菜单 **File → Options → Accounts**。
2. 点 **GitHub.com → Sign in**，会弹浏览器，在浏览器里登录（有两步验证就按提示做）。
3. 回到 Desktop，看到自己的头像和用户名 = 登录成功。

> 没有账号的人：先在 https://github.com 注册（用常用邮箱），然后把用户名发给 C，让仓库所有者把你加进 **Settings → Collaborators**。**没被邀请就看不到仓库，Clone 会报 404。**

### 2.3 把仓库克隆到自己电脑（这就是"第一次下载"）
1. Desktop 菜单 **File → Clone repository…**
2. 选上方 **URL** 标签，粘贴：

   ```
   https://github.com/qicheng523/course-scheduler.git
   ```

3. **Local path** 选一个你找得到的文件夹。**建议用纯英文路径**，例如
   `D:\projects\course-scheduler`（中文路径能跑，但以后终端里显示中文容易乱码，能避就避）。
4. 点 **Clone**，等进度条走完。

> ⚠️ 旧文档里写的 `coruse-scheduler` 是**拼写错误**，以本手册的 `course-scheduler` 为准。
> ⚠️ **千万不要用 GitHub Desktop 的 "Create new repository" 或 "Publish"**。项目仓库已经存在，你只是在克隆它；用错会把仓库建到别的地方，搞得一团乱。

### 2.4 克隆完先让项目跑起来（`.venv` 不在仓库里，这是正常的）
仓库里**故意不传** `.venv/` 和 `data/app.db`（理由见 §8），所以克隆下来是"干净代码"，要自己装一次环境。照着 [README](../README.md) 做：

```powershell
cd D:\projects\course-scheduler
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

然后跑测试和启动：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

浏览器打开 `http://127.0.0.1:8000/health`，看到 `{"ok":true}` 就成了。

> 装完后你的文件夹里会多出 `.venv/`，但 GitHub Desktop 的 Changes 里**看不到它**——这是**对的**，它被 `.gitignore` 拦住了。看不到 = 好事。

### 2.5 第一次配置的自检（5 条全对才继续）

- [ ] 左上角显示 `course-scheduler`，分支是 `main`。
- [ ] 左侧点 **Changes**，显示 **"No local changes"**（没改动）。
- [ ] 文件夹里能看到 `app/`、`data/`、`docs/`、`tests/`、`README.md`。
- [ ] 文件夹里除了你自己装的 `.venv/`（正常）和隐藏的 `.git/`，没有多出来的怪东西（比如 `venv/`、`backup-2026-xx/` 这种别人机器上的残留）。
- [ ] 浏览器打开 https://github.com/qicheng523/course-scheduler 能看到项目。

---

## 3. 每天怎么"下载文件"（Pull 的三种情况）

### 3.1 先分清 Fetch 和 Pull
- **Fetch origin**：只去云端问"有没有新的"，**不改变你电脑上的文件**。点完如果落后，按钮会变成 **Pull origin (数字)**。
- **Pull origin**：真的把新文件**下载并合并**到你电脑。**这才是"下载文件"。**

**记住：每次开工先 Fetch，看到 Pull 就点 Pull。** 一天至少拉一次（20:00 开工统一拉）。

### 3.2 三种情况照做

| 情况 | 你看到什么 | 怎么做 |
|---|---|---|
| 本地没改过文件 | Fetch 后出现 **Pull origin** | 直接点 **Pull origin** |
| 本地有改动还没提交 | 提示你还有没提交的改动 / Pull 后报错 | **先 Commit**（写 `WIP` 也行），再 Pull；Pull 完再继续干 |
| Push 被拒绝（rejected） | 红字 `Updates were rejected…` | **先 Pull origin，再 Push origin**；出现冲突就停手找 C |

### 3.3 只想看/拿某一个文件，不想动整个项目
1. 浏览器打开仓库 → 点进那个文件。
2. 右上角点 **Raw** → 右键"另存为"，或直接复制内容。
3. **这只适合"看/参考"**，不要拿它去覆盖项目里的文件再提交（容易把别人的改动冲掉）。

### 3.4 换电脑 / 重装系统
不要复制旧文件夹（`.git` 复制过去容易坏）。**重新按 §2.3 Clone 一遍**，最干净。

### 3.5 不推荐的两个做法
- ❌ **网页上 Code → Download ZIP**：下载下来的是"没有历史的一次性文件"，不能提交，也拿不到以后更新。只适合临时看看。
- ❌ **把别人的文件用微信发给你再覆盖**：会覆盖掉自己和队友的改动，`git` 也记不到。

> 紧急情况（只改文档、身边没电脑）：可以在网页上点 **Add file → Upload files** 改一个说明文档，改完立刻在群里说一声，回电脑后**先 Pull** 再继续。**代码永远不在网页上改。**

---

## 4. 每天怎么"提交文件"（Commit + Push，6 步）

### 第 1 步：打开仓库，对一下身份
打开 GitHub Desktop，看左上角 **Current repository** 是不是 `course-scheduler`。不是就点它切过去。

### 第 2 步：点 Changes，只勾自己的文件
- 左侧点 **Changes**，这里列出你改过/新增过的所有文件。
- 每个文件左边有**复选框**：**只勾自己负责的文件**（对照 §5 分工表），别人的、你看不懂的、`.venv` 类的**全部取消勾选**。
- 如果一次出现**几百上千个文件**，或者看到 `.venv`：**先别 Commit**，关掉重开 Desktop；还在就截图发群 @C（说明 `.gitignore` 没生效）。

### 第 3 步：点开文件看 diff（30 秒，能救命）
点文件名，右边会显示改了哪里：**绿色 + 是新增，红色 − 是删除**。
- 顺便检查：有没有把**密码/密钥/真实姓名/学号**写进去（示例数据一律用"老师A~H"）。
- 有没有乱码（中文变成 `\346\226…`）。乱码在 Desktop 里看不出来就去 VS Code 里看。

### 第 4 步：写 Summary（提交说明）
格式固定：`代号: 干了啥`，一句话说清。

| 好例子 | 为什么好 |
|---|---|
| `C: 加了空闲段计算和 12 个测试` | 谁、做了什么、有没有测试 |
| `A: 课程页加课表单接上真接口` | 一眼知道进度 |
| `B: reset_db 一条命令恢复 19 门课` | 带数字，可验证 |

| 坏例子 | 问题 |
|---|---|
| `update` / `改了一下` | 看不出改了啥 |
| `C: 修 bug` | 什么 bug？ |
| `asdf` | 等于没写 |

Description（第二栏）可选：写**怎么验证的**，比如 `pytest 7 passed`、`浏览器 375px 不横滑`。

### 第 5 步：点 Commit to main
按钮在左下角。点完 Changes 变空，说明"存档"成功（**但还没上传**）。

### 第 6 步：点 Push origin
右上角出现 **Push origin ↑1** 就点它（1 = 你有 1 条待上传）。等它变回 **Fetch origin** = 上传成功。

**最后验证（10 秒）**：浏览器打开仓库 → 点 **Commits**，能看到你写的那句话；或者 Desktop 点 **History**，最上面一条就是你。**看到 = 队友能拿到。**

### 4.1 一天要提交几次？
- **完成一小步就 Commit**（存档越多越安全，出错能回到上一步）。
- **Push 至少收工一次**，最晚 **22:15 前**必须推上去，否则 22:30 站会别人看不到你的活（"没 push = 没做"）。
- 建议节奏：上午/下午各 1 次 Commit，晚上收工 1 次 Commit + 1 次 Push。

### 4.2 提交错了怎么办？
- **还没 Push**：在 **History** 里找到最上面那条，点 **Undo**，改好重新提交。
- **已经 Push 了**：**不要试图"撤销历史"**（会害到队友）。直接再改一次、再提交一次，Summary 写 `C: 修正上一条，xxx` 即可；拿不准就问 C。
- **点错了 Discard changes**：未提交的改动**永久消失**，找不回来。→ 这就是红线里不让点的原因。

---

## 5. 三人分工：谁改哪些文件（一人一格）

| 角色 | 负责的文件/目录 | 说明 |
|---|---|---|
| **C** 后端/算法/集成 | `app/main.py`、`app/db.py`、`app/models.py`、`app/routers/`、`app/services/`、`tests/`、`docs/API.md` | 表和接口、排程算法、测试 |
| **A** 前端/QA/演示 | `app/templates/`、`app/static/`、`docs/UI.md`、`docs/wireframes/` | 页面、样式、演示截图 |
| **B** 数据/部署/文档 | `scripts/`、`data/`、`.github/`、`README.md`、`docs/SETUP.md`、`docs/DEPLOY.md` | 种子数据、一键重建、部署、文档 |
| **共管**（改前群里说） | `requirements.txt`、`pytest.ini`、`.gitignore`、`TEAM.md` | 加依赖要先说"理由 + 替代方案 + 安装命令"，三个人同意 |

**三条落地规则**
1. **一个文件只有一个主人**；要改别人的文件，先在群里说一句、等对方回"可以"。
2. **提交前对照分工表**：Changes 里勾的文件必须全是你名下的（共管文件除外）。
3. 新文件（比如新页面、新脚本）先在群里说一句，明确归谁，再开始写。

> 本手册 `docs/GitHub每日操作手册.md` 归**全组共管**。
> `docs/API.md` 是 C 的，`docs/SETUP.md`、`docs/DEPLOY.md` 是 B 的，`docs/UI.md` 是 A 的——别写错文件。

---

## 6. 每天的固定节奏（和任务卡一致）

| 时间 | 谁 | 做什么 | Desktop 里对应 |
|---|---|---|---|
| 20:00 | 三人 | 同步最新代码（开工） | **Fetch origin → Pull origin** |
| 20:10–21:40 | 三人 | 各改各的文件 | 用 VS Code 改；每完成一小步可 Commit |
| 21:40 | C | 接口好了，群里喊一声 | A/B 再 **Pull** 一次接真接口 |
| 22:00 | 三人 | 跑验收三条 + 截图 | 截图存 `evidence/`（见 §7） |
| 22:15 前 | 三人 | 提交代码 + 证据并推送 | **Commit to main → Push origin** |
| 22:30 | 三人 | 站会四句话 | 群里发，附 commit 短号 |

**站会四句话模板**（照着填，别长篇大论）：
1. 昨天完成：`C：空闲段 12 个测试全绿（30c1a88）`
2. 今天要做：`A：课程页列表 + 加课表单`
3. 卡在哪：`B：seed 重复执行会插两次，等 C 看一眼`
4. 今天砍什么：`C：把 /api/slots 的路由推到明天`

> commit 短号在 Desktop 的 **History** 里每条的右边（7 位，比如 `30c1a88`），站会贴它队友能直接查。

---

## 7. 证据怎么交（"没有证据 = 没做"）

- 每天 22:00 验完，把**截图/终端输出**放进仓库 `evidence/` 下**当天目录**，例如 `evidence/D03/`。
- 当天目录名以 **C 在群里公布的为准**（D 编号有时和日期差一位，别自己猜）。
- 文件名带**自己的代号**，避免同名冲突：
  - `evidence/D03/A-课程页.png`
  - `evidence/D03/B-reset后19门课.png`
  - `evidence/D03/C-pytest.txt`
- 截图里**不要出现**真实姓名、学号、手机号、密码；示例数据用"老师A~H"这类假名。
- 证据和代码**一起 Commit + Push**：`A: 加课程页 + D03 截图`。
- 当天的 `evidence/D03/README.md` 由 **C** 汇总写，别人不要动。

---

## 8. 绝对不许提交 / 不许做的事

| 东西 / 操作 | 为什么 | 正确做法 |
|---|---|---|
| `.venv/`、`venv/` | 几百 MB，GitHub 会拒收，队友拉不动 | 每人在自己电脑装（§2.4） |
| `__pycache__/`、`.pytest_cache/` | 缓存垃圾，天天变 | 已被 `.gitignore` 拦住，别手动提交 |
| `data/app.db` | 每次启动自动重建，传了也没用 | 要 19 门课就跑 `scripts/reset_db.py` |
| `.env` / 密码 / 密钥 / 真实个人信息 | 泄露风险，公开仓库会出事 | 示例数据用假名；密钥不进仓库 |
| `force push` | 会覆盖队友的提交，找不回来 | 只 Pull 再 Push |
| 点 **Discard changes** | 未提交改动永久消失 | 有改动就 Commit，哪怕写 `WIP` |
| 网页上直接改代码 | 绕过本地测试，容易冲突 | 只在紧急改文档时用，且改完群里说 |
| **Create new repository / Publish** | 会造出第二个仓库 | 只 Clone 现有仓库 |
| **Download ZIP** | 没有历史，不能提交 | 用 Clone / Pull |
| 微信传代码文件 | 互相覆盖、查不到历史 | 只走 git |

> 提示：`明天-*.md`、`tools/`、`backup-*/`、`docs-plan.md`、`data/app.db` 这几类被 `.gitignore` **故意忽略**——如果你的文件在 Changes 里"消失"了，多半是名字/位置撞上了这些规则，改个名字或问 C。

---

## 9. 出错了怎么办（先查表，别自己乱点）

| 你看到的提示 / 现象 | 意思 | 怎么办 |
|---|---|---|
| `Updates were rejected because the remote contains work…` | 云端有别人的新提交，你落后了 | 点 **Pull origin** 再 **Push origin**；有冲突找 C |
| `Repository not found` / 404 | 没登录 / 没被邀请 / 地址写错 | 浏览器打开仓库链接，能看见就是真存在；看不见找 C 发邀请 |
| `Authentication failed` | 登录过期 | **File → Options → Accounts** 重新登录 |
| `You have uncommitted changes` | 本地改动没提交，不能 Pull | 先 **Commit**（写 `WIP` 也可），再 Pull |
| Changes 里几千个文件，还有 `.venv` | `.gitignore` 没生效或克隆不完整 | **先别 Commit**，重开 Desktop；还在就截图发群 @C |
| 要提交的文件在 Changes 里找不到 | 被 `.gitignore` 忽略了 | 改名字/改目录；拿不准问 C |
| 文件旁边有 `x`，提示 **conflicts** | 你和队友改了同一个文件的同一处 | **停手**，截图发群 @C；别乱点"解决" |
| 提交了但网页上没有 | 只 Commit，没 Push | 点 **Push origin** |
| 顶部显示 `This branch is 3 commits behind` | 落后云端 3 条 | 点 **Pull origin** |
| 终端里中文变成 `\346\226…` | 命令行编码问题 | 不影响提交；用 Desktop / VS Code 看文件 |
| `ModuleNotFoundError: No module named 'xxx'` | 没装依赖 / 没激活虚拟环境 | 按 §2.4 装；或用 `.\.venv\Scripts\python.exe -m pytest -q` |
| 网络一直转圈 | GitHub 访问慢 | 别狂点；等 2 分钟再 Fetch；换网络再试 |

**不确定时的唯一正确动作**：**不要点任何按钮**，截图发群，@C 或 @B。花 1 分钟问，比丢 2 小时代码便宜。

---

## 10. 常见问题（FAQ）

**Q1：我怎么知道队友改了什么？**
Desktop 点 **History**，或浏览器仓库点 **Commits**；点开一条能看到具体改了哪几个文件、改了什么。

**Q2：可以一天都不 Push 吗？**
不行。收工必须 Push。不 Push = 队友拿不到 = 你没做（验收规则）。

**Q3：两个人同时改了同一个文件怎么办？**
**先停手**。改文件前对照分工表；真要改别人的文件先群里说。已经冲突了：截图发群 @C，别自己点"解决"。

**Q4：我的文件为什么没出现在 Changes 里？**
被 `.gitignore` 忽略（见 §8 末尾的清单），或者你改的不是这个仓库里的文件（路径选错了）。

**Q5：家里和学校两台电脑怎么弄？**
各自 Clone 一份（§2.3）。换电脑前先 **Push**，到另一台先 **Pull**。不要用 U 盘/微信拷文件夹。

**Q6：提交信息写错了要紧吗？**
没 Push：History 里 Undo 重写。已 Push：不要改历史，下次写好；在群里说明一句即可。

**Q7：我能删队友的文件吗？**
不能。要删先在群里说，让文件主人自己删。

**Q8：我能加新依赖（新库）吗？**
不能自己加。先说明**理由 + 替代方案 + 安装命令**，三个人同意后，由 B 改 `requirements.txt`，其他人 Pull 后重新 `pip install -r requirements.txt`。

**Q9：我想看某个旧版本的文件？**
History 里点那条提交，右边能看到当时的文件内容（只读）。别用 `git checkout` 去改文件，容易把现状搞乱。

**Q10：Desktop 里能直接改文件吗？**
不能，也**不要**。Desktop 只负责"看改动、提交、推送"；改文件用 **VS Code**（菜单 **Repository → Open in Visual Studio Code**）。

---

## 11. 已知的"旧文档坑"（别被带偏）

1. **仓库名**：旧文档写 `coruse-scheduler`，是拼写错误。实际是 **`course-scheduler`**。
2. **分支**：`docs/技术栈与目录说明.md` 里说"一人一个分支、main 保护"——**已过时**。全组只走 `main`，直接 Commit to main，不建分支、不用 PR。
3. **危险命令**：`给队友看的-文件分工与GitHub.md` 第 8 节里的 `git reset` / `git checkout` 命令**都不要用**；需要回退找 C。
4. **D 编号**：文档里的 D 编号和日期偶尔差一位，**证据目录以 C 当天在群里公布的为准**。
5. **README 的 "2 passed"** 已过时（测试已经更多了），以实际 `pytest` 输出为准，等 B 收尾时更新 README。

---

## 12. 直接复制到群里的公告版

```
【Git 手册】docs/GitHub每日操作手册.md 已写好，今晚 20:00 前每人做完第一次配置：
1) 官网装 GitHub Desktop 2) 登录自己的 GitHub 账号 3) Clone 仓库（URL 见手册 §2.3）
4) 按 README 装 .venv 并跑通 pytest 5) 自检 5 条。

以后每天：
- 20:00 开工先 Fetch → Pull
- 22:15 前 Commit to main → Push origin（只勾自己的文件）
- 冲突/报错先截图发群，不要乱点按钮
- 五条红线：不 force、不 Discard、冲突停手、代码不走微信、不传 .venv/data/app.db/真实信息
旧文档里仓库名 coruse-scheduler 是错的，以手册为准。
```

---

## 附：一页贴墙版（打印出来贴屏幕边）

```
┌─────────────── 每天开工 ───────────────┐
│ 1. 打开 GitHub Desktop                  │
│ 2. 左上角是 course-scheduler             │
│ 3. Fetch origin → Pull origin（有就点）  │
└─────────────────────────────────────────┘
                ↓ 只改自己的文件（VS Code）
┌─────────────── 每天收工 ───────────────┐
│ 4. Changes → 只勾自己的文件              │
│ 5. 点开文件看 diff（没有密码/乱码）       │
│ 6. Summary：代号: 干了啥                 │
│ 7. Commit to main                        │
│ 8. Push origin                           │
│ 9. 网页看到自己的提交 = 成功             │
│ 10. commit 短号 + 截图发群里             │
└─────────────────────────────────────────┘
红线：不 force｜不 Discard｜冲突停手找 C
      代码不走微信｜不传 .venv / data/app.db / 真实信息
```
