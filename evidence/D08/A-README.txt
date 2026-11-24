A · 11-24 交付证据
==================

一、U5 收尾（打卡状态只认服务端）
--------------------------------
代码：plan.js 已无任何 localStorage 引用（grep app/ = 0 处）。
验证：
- 普通窗口点打卡 → 变灰 ✅，统计已完成 +1
- 全新用户目录（等价无痕窗口）直接打开 / → 同一任务仍显示 ✅，
  统计已完成=2（当次数据库有 2 条打卡），localStorage 记录=0
- 375px：scrollWidth=375
截图：A-incognito-features-375.png

二、计划页新增界面（代码已完，成功路径待 C 接口）
------------------------------------------------
1. 「删除本周计划」按钮（本周报告底部），二次确认文案：
   “删除本周计划？这会一起清掉这一周的打卡记录，任务回到待排状态。”
2. 「加一个任务」表单：标题 / 类别（作业、C语言、项目、刷题、CS50）/
   时长（分钟）/ 优先级（1–3，按 docs/API.md 的 task 表）/ 截止时间
3. 每个任务块右侧：「改时间」「删除」两个按钮（不做拖拽）；
   改时间展开两个时间框 + 保存/取消
4. 待排任务列表：GET /api/tasks 成功后显示标题/类别/时长/优先级

三、当前阻塞（重要）
--------------------
截至 2026-11-24 本机验证时，C 的 v0.8 接口**还没推到仓库**：
- 远程 main 最新仍是 665d617
- docs/API.md 没有 §3⑪⑫⑬ / v0.8
- 下列路由不存在：
  DELETE /api/plan/{week_start}
  GET/POST /api/tasks
  DELETE /api/block/{id}
  PATCH /api/block/{id}

因此今天四块新界面的**成功路径无法做真实联调**，只验证了失败分支：
- 删除计划 → “后端还没有删除计划的接口（等 C 推送）。”
- 加任务 → “后端还没有 /api/tasks 接口（等 C 推送）。”
- 改时间 → “后端还没有修改时间块的接口（等 C 推送）。”
- 删除块 → “删不了：后端还没有这个接口（等 C 推送）。”

前端按以下约定接线（请 C 确认）：
- POST /api/tasks body：
  {title, category, duration_min, deadline: "YYYY-MM-DDTHH:mm:00", priority}
- GET /api/tasks：{"items": [...]} 或直接数组，两者都能渲染
- DELETE /api/block/{id}、DELETE /api/plan/{week_start}：成功 204
- PATCH /api/block/{id} body：{"start": "HH:mm", "end": "HH:mm"}

四、回归
--------
pytest -q → 49 passed（C 的 4 个接口测试还没进仓库，目标 ≥55 待 C）
node --check app/static/plan.js → OK
375px：无横向滚动

五、U7
------
tools/verify_d03.py 不在仓库，仍需总纲验收机复跑。
