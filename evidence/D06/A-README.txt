A · 11-22 交付证据
==================

做了什么
--------
1. base.html 导航：首页 / 课程 / 计划（健康检查换成 /plan）
2. plan.js：任务行打卡按钮、本周统计卡、导出周报链接
3. style.css：打卡按钮 44px、已打卡变灰划线、统计卡 375px 两列

验证（本机，Windows，Python 3.12）
----------------------------------
$ .venv\Scripts\python.exe -m pytest -q
...............................................                          [100%]
47 passed

$ node --check app/static/plan.js
plan.js 语法 OK

接口（真实数据：course=19 fixed_event=35 task=5，计划 45 块）：
GET /                       -> 200（首页=计划页）
GET /courses                -> 200
GET /plan                   -> 200
GET /api/stats/week?week_start=2026-11-16
  -> totals {"scheduled":5,"done":0,"unscheduled":0,"planned_minutes":375}
GET /api/export.md?week_start=2026-11-16
  -> 200, text/markdown; charset=utf-8,
     Content-Disposition: attachment; filename="export-2026-11-16.md"
     （中文正常，7 天小节齐全）

浏览器实测（Edge 无界面，375×812，手机模拟）
--------------------------------------------
U1 导航三个入口：首页/课程/计划，逐个打开都是 200         PASS
U2 点第一行任务「打卡」：变灰 + 已打卡 ✅ + 按钮禁用       PASS
   F5 刷新后：仍是已打卡（浏览器本地存储记住）            PASS
U3 再点一次：按钮禁用无效；接口重复 PATCH 返回
   created:false，checkin 表仍只有 1 行，stats.done 仍为 1  PASS
U4 本周统计卡：5 已排 / 1 已完成 / 0 未排 / 6 小时 15 分钟
   与 /api/stats/week 的 totals 完全一致                 PASS
U5 导出：链接 /api/export.md?week_start=2026-11-16，
   下载 .md 中文正常，7 天都在，打过的任务带 ✅            PASS
U6 375px：document.documentElement.scrollWidth = 375      PASS

U7 说明：tools/verify_d03.py 不在仓库里（只在总纲机器上），
本机无法执行，上面 U1–U6 用浏览器 + 接口逐条复现。

截图
----
A-checkin-375.png  打卡后 / 刷新后（整页）
A-stats-375.png    本周统计卡（4 个数字 + 导出按钮）
A-export-375.png   下载的 .md 在浏览器里打开（中文正常）
A-export.md        导出的原始 Markdown

注意
----
打卡记录是测试数据，截图拍完已从本地 data/app.db 清掉；
总纲验收时自己点一次即可复现 U2/U3。
