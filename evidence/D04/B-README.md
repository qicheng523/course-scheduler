# D04 证据包 · B 的任务进 seed

> 日期：2026-11-20（D4）｜负责人：B
> 这一包证明 D4 卡：**任务卡 §5 的 5 条冻结任务进 `scripts/seed.py`，幂等，smoke 核对升级**。

## 里面有什么

| 文件 | 是什么 |
|---|---|
| `B-seed-v2.txt` | 完整预演原始输出：重置 → 灌入（19 课 + 35 固定事件 + 5 任务）→ 核对任务字段 → 再跑一遍（19/35/5 不翻倍）→ `pytest -q` 26 passed |

## 过线三条

1. **验收项真跑过**：seed 两次执行后 `course=19 fixed_event=35 task=5`（不翻倍）；5 条任务的标题/分类/时长/截止/优先级与 `tests/test_plan.py` 里的冻结清单逐字一致；`pytest -q` → 26 passed（C 的 plan 测试 import seed.py，证明没改坏）
2. **没改别人的文件**：只动了 `scripts/seed.py`、`.github/workflows/ci.yml`、`data/README.md`、`evidence/D04/`、`工作日志.md`，全在 B 的地盘
3. **昨天能跑的今天还能跑**：26 个测试全绿

## 改了哪三处

1. `scripts/seed.py`：新增 `SEED_TASKS`（5 条，字段照 docs/API.md §1 ③）；seed 现在清空并重灌 `course / fixed_event / task` 三张表，**不碰** `plan / block / checkin`；`FIXED_EVENTS / parse_seed_courses / to_min` 三个被 C 测试引用的名字原样保留
2. `ci.yml`：smoke 核对升级为 `(19, 35, 5)`，task 表最后必须恰好 5 条——**这就是"smoke 不会把 task 表清掉"的机器证明**
3. `data/README.md`：补上 seed 三件套清单和 reset_db 的警告

## 备注

- CI 里 smoke 的"重置"只发生在 GitHub 的一次性机器上，清的是临时库；本地真库不要乱跑 `reset_db.py`（它会清掉计划/打卡）
- 任务卡 §5 的数字是冻结的，改之前先在群里说（`tests/test_plan.py` 里还有一份同样的清单）
- 任务 1（线性代数第二章习题）截止 2026-11-20 23:59：过了今晚 23:59 再生成计划，它会按算法进 `unscheduled`（"截止时间已过"）——这是正常行为，演示前留意日期
