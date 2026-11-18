# D02 证据包 · B 的种子数据

> 日期：2026-11-18（D2）｜负责人：B
> 这一包证明 G1 里 B 的卡已经过线：**`scripts/seed.py` + `scripts/reset_db.py`，19 条真实课表（9 节模型）+ 固定事件**。

## 里面有什么

| 文件 | 是什么 |
|---|---|
| `B-seed-output.txt` | 完整流程原始输出：重置空库 → 灌入 19 课 + 35 固定事件 → 再跑一遍验证幂等 → 数据库核对 |
| `B-curl.txt` | curl 原始输出：`/health` 200、`/api/courses?term=2026f` 返回 `total=19` |

## 过线三条

1. **验收项真跑过**：`GET /api/courses?term=2026f` → HTTP 200、`total=19`，字段名与 `docs/API.md` §3 一致（`name / weekday / start / end / location`，无教师字段）
2. **没改别人的文件**：只动了 `scripts/`（B 的地盘）和 `evidence/D02/`（公共证据），没碰 `app/`、`tests/`、`templates/`
3. **昨天能跑的今天还能跑**：`python -m pytest -q` → `7 passed`

## 怎么复现（PowerShell，项目根目录）

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/reset_db.py --yes   # 重置成空库
python scripts/seed.py             # 灌入 19 课 + 35 固定事件
python -m uvicorn app.main:app --reload
```

然后浏览器打开 <http://127.0.0.1:8000/api/courses>，应看到 `"total":19`。

## 备注

- `seed.py` 的数据源是 `data/seed-courses.txt`（B 维护）：**以后改课表只改 txt，不用动代码**；txt 里的"老师A~H"是脱敏记录，课程表没有教师字段，不进库
- `seed.py` 只清空并重灌 `course` / `fixed_event` 两张表，**不碰** `task` / `plan` / `block` / `checkin`
- 固定事件（睡觉/三餐/午休/英语班）写在 `scripts/seed.py` 顶部的 `FIXED_EVENTS` 清单里，按真实作息改；午休那几行如果想让排程用中午时间，直接删掉
- 第 9 节（18:00-20:35 晚自习）是空闲时间，按约定**没有**灌进课表
- `data/app.db` 不进仓库（.gitignore 已排除），每次演示前 `reset_db.py` + `seed.py` 即可得到干净演示数据
