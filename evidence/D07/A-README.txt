A · 11-23 交付证据
==================

做了什么
--------
1. plan.js 按合同 v0.7 改：删掉 localStorage 那一套
   （checkinKey / isChecked / rememberChecked / clearWeekCheckins / 对账逻辑，约 60 行），
   改成直接读 GET /api/plan/{week_start} 返回的 blocks[].done。
2. 打卡成功后仍然即时变灰 + ✅，统计卡立刻刷新；刷新/换浏览器状态以数据库为准。
3. base.html 页脚：骨架版本 v0.1.0 → 版本 v0.6。

验证（本机，Windows，Python 3.12）
----------------------------------
$ .venv\Scripts\python.exe -m pytest -q
49 passed

$ node --check app/static/plan.js
plan.js OK

浏览器实测（Edge 无界面，375×812，手机模拟）
--------------------------------------------
A. 浏览器 A（普通配置）
   点第一行任务「打卡」：
   - 今日区 + 本周安排里同一任务都变灰 + 已打卡 ✅（同一任务渲染两处，属正常）
   - 统计卡「已完成」= 1
   - localStorage 里 checkin 相关 key = 0（已确认不再用浏览器存储）
   F5 刷新后：仍显示已打卡，统计仍 1。

B. 浏览器 B（全新用户目录，等价于无痕窗口 / 换电脑）
   直接打开 /：
   - 同一任务仍是已打卡 ✅ ×2
   - 统计卡「已完成」= 1
   - localStorage checkin key = 0
   → 证明打卡状态来自数据库，不是浏览器本地。

C. 清空数据库里的打卡记录（delete from checkin）后刷新浏览器 B：
   - 已打卡行 = 0
   - 统计「已完成」= 0
   - 6 个打卡按钮全部恢复可点「打卡」
   → 11-22 的“重置后按钮不归零”问题彻底消失（服务端唯一真源）。

D. 375px：document.documentElement.scrollWidth = 375，无横向滚动。
E. 页脚显示：版本 v0.6 · 数据库文件：...\data\app.db

U7 说明
-------
tools/verify_d03.py 不在仓库里（只在总纲验收机上），本机无法执行；
以上是浏览器 + 接口逐条实测。

截图
----
A-incognito-375.png   浏览器 B（无痕等价）打开首页，任务已打卡 ✅
