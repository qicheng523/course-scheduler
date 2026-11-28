# DEPLOY.md · 部署手册（**未部署**，保留为可选步骤，B 维护）

> ⚠️ **状态（2026-11-28）：本项目的公网部署没有做，也不在本次交付范围内。**
> 本次提交只要求两份东西：**一份说明功能的文档 + 仓库链接**。所以这个文件是"如果以后要上线"的参考，不是待办。
> 为什么可以不做：免费层有两个硬伤——① 15 分钟没人访问会休眠，第一次打开要等 30–50 秒；② 没有持久磁盘，SQLite 文件在重启/重新部署后会被清空，演示数据全丢。而"能跑"的证据我们已经有 57 个测试 + 54 项验收脚本 + README 里 5 条命令。
>
> 下面的步骤是 11-21 的预演记录，**未执行到上线**，不要当成"已完成"。

---

## 1 选 Render 的理由

| 方案 | 免费层 | 结论 |
|---|---|---|
| **Render** | 不用信用卡、从 GitHub 直接部署、自带 HTTPS 域名 | ✅ 用这个 |
| Fly.io | 注册就要信用卡 | ❌ 放弃 |

## 2 部署步骤（D10 由 B 执行，需要 Render 账号）

1. 打开 <https://render.com> → **Sign up with GitHub** → 授权时**勾选私有仓库权限**（我们的仓库是私有的）
2. Dashboard → **New +** → **Web Service** → 选择仓库 `qicheng523/course-scheduler`
3. 配置（其余全默认）：

   | 项 | 填什么 |
   |---|---|
   | Name | course-scheduler |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |

4. 点 **Create Web Service**，等 Build + Deploy 完成（约 2-5 分钟）
5. **部署完成后第一件事：灌数据**。免费层磁盘是临时的，仓库里没有 `app.db`，应用启动只会建空表。Render 服务页 → **Shell** 标签 → 输入：

   ```bash
   python scripts/reset_db.py --yes && python scripts/seed.py
   ```

   然后打开链接 → 首页点"生成计划"，报告里应该有数字（19 课 / 5 任务）。
6. **演示当天**：提前 5-10 分钟先点开一次链接——免费层 **15 分钟无访问会休眠**，冷启动要 1-2 分钟，别让答辩现场等它醒。

## 3 本地预演结果（2026-11-21）

启动命令用本机模拟 Render 的方式验证过（证据 `evidence/D05/B-deploy.txt`）：

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8100
```

- `GET /health` → 200 `{"ok":true}`
- `GET /` → 200（本周报告页）
- 结论：**命令本身没问题，剩下的就是注册账号 + 点鼠标**

## 4 卡点（为什么今天只到"预演"）

真实部署需要 B 用自己的 GitHub 账号登录 Render 并授权私有仓库——**这一步只能人来做**。按任务卡"60 分钟不通就停，把卡点写进文档"的规则，停在这里，D10 执行本手册 §2。

## 5 坑（D10 前记住）

| 坑 | 说明 |
|---|---|
| 数据会被清空 | 免费层磁盘临时：**每次重新部署后 app.db 归零**，必须重跑 §2 第 5 步的 seed |
| 别传 app.db | `.gitignore` 已排除；Render 拉的是仓库，本地库不会上去（好事，见上一条） |
| 私有仓库授权 | Render 授权 GitHub 时要勾私有仓库权限，否则列表里找不到 course-scheduler |
| 砍单顺序 | 若 D10 Render 卡住超过 60 分钟，按 TEAM.md 砍单顺序砍"公网部署"，演示改为本机，不影响及格 |
