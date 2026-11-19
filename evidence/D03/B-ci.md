# D03 证据包 · B 的 CI

> 日期：2026-11-19（D3）｜负责人：B
> 这一包证明 B 的 D3 卡：**`.github/workflows/ci.yml` 上线，以后每次 push 自动检查**。

## 里面有什么

| 文件 | 是什么 |
|---|---|
| `B-pytest.txt` | CI 上线前的本地基线：`pytest -q` → **17 passed** + `check_env.py` 7 个依赖全 OK |
| `B-seed-smoke.txt` | 按 CI 第 4 步顺序本地预演：重置 → 灌入 → 核对 → `seed OK：course=19 fixed_event=35` |

## CI 干什么（.github/workflows/ci.yml）

每次 push / PR 自动在 GitHub 的机器上跑 4 步：

1. 装 Python 3.12 + 依赖（requirements.txt 锁死版本）
2. 环境自检（7 个依赖 [OK]）
3. `python -m pytest -q`（过线标准：17 passed 起步）
4. seed 冒烟：重置 → 灌入 → 核对 19 课 + 35 固定事件（保证数据脚本没坏）

**目的**：谁把代码弄坏了，GitHub 上立刻红 ✗，不用等第二天站会才发现。

## 怎么看结果

GitHub 仓库 → **Actions** 标签页 → 最新一次 run：

- 绿色 ✓：全过
- 红色 ✗：点进去 → 看哪一步挂了 → 把报错截图发群里

## 怎么复现（本机不用等 GitHub，一样能跑这 4 步）

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/check_env.py
python -m pytest -q
python scripts/reset_db.py --yes
python scripts/seed.py
```

## 备注

- CI 文件归 B（`.github/` 是 B 的地盘）；改 workflow 不用问别人，但改了要在群里说一句
- 真实 CI 结果以 GitHub Actions 页面为准（本机环境 ≠ GitHub 环境，两边都绿才算过）
- 团队内部规划文档（`明天-*.md` 等）在 .gitignore 里，不会传到仓库，CI 也看不到
