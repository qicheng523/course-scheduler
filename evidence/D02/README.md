# D02 证据包 · 课程接口

> 日期：2026-11-18（D2）｜负责人：C
> 这一包证明 **G1「网页能加课、刷新还在」** 的后台部分已经通了。

## 里面有什么

| 文件 | 是什么 |
|---|---|
| `pytest.txt` | `python -m pytest -q` 的原始输出（7 passed） |
| `curl.txt` | 6 条 curl 的原始输出：查 / 加 / 冲突 409 / 再查 / 星期 422 / 时间倒置 422 |

## 怎么自己复现（PowerShell 5.1）

> **为什么用文件传 JSON**：Windows PowerShell 5.1 直接把中文 JSON 写在命令里，会丢引号、中文变问号。
> 先写成 **UTF-8（无 BOM）文件**，再用 `--data-binary "@文件名"`，最稳。

```powershell
# 1) 起服务（这个窗口别关）
cd "D:\dsh-workspaces\课表排程工作区"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload

# 2) 另开一个 PowerShell，回到项目根目录
cd "D:\dsh-workspaces\课表排程工作区"

# 3) 准备 3 个 JSON 文件（复制这一整段，一次跑完）
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText("$PWD\body-add.json",        '{"name":"高等数学AI","weekday":1,"start":"08:00","end":"09:40","location":"1-0206"}', $utf8)
[System.IO.File]::WriteAllText("$PWD\body-conflict.json",   '{"name":"线性代数","weekday":1,"start":"09:00","end":"10:30","location":"1-0206"}', $utf8)
[System.IO.File]::WriteAllText("$PWD\body-badweekday.json", '{"name":"周末课","weekday":6,"start":"10:00","end":"11:00"}', $utf8)

# 4) 查（空库）
curl.exe -sS -w "`n[HTTP %{http_code}]`n" "http://127.0.0.1:8000/api/courses?term=2026f"

# 5) 加一门课
curl.exe -sS -w "`n[HTTP %{http_code}]`n" -X POST "http://127.0.0.1:8000/api/courses" -H "Content-Type: application/json" --data-binary "@body-add.json"

# 6) 再查一次（这条能看见课，就说明"刷新还在"）
curl.exe -sS -w "`n[HTTP %{http_code}]`n" "http://127.0.0.1:8000/api/courses?term=2026f"

# 7) 失败场景：时间重叠
curl.exe -sS -w "`n[HTTP %{http_code}]`n" -X POST "http://127.0.0.1:8000/api/courses" -H "Content-Type: application/json" --data-binary "@body-conflict.json"

# 8) 失败场景：星期 6
curl.exe -sS -w "`n[HTTP %{http_code}]`n" -X POST "http://127.0.0.1:8000/api/courses" -H "Content-Type: application/json" --data-binary "@body-badweekday.json"

# 9) 收尾：删演示数据（B 的 seed 会重新灌 19 条）
Remove-Item data\app.db -Force
Remove-Item body-*.json -Force
```

## 预期结果（和 curl.txt 一致）

| 步骤 | 期望 |
|---|---|
| 查空库 | `{"items":[],"total":0}` + 200 |
| 加课 | 带 `id` 的记录 + 201 |
| 再查 | `total` 变成 1 |
| 重叠 | `{"detail":"这门课和「高等数学AI」时间冲突"}` + 409 |
| 星期 6 | `{"detail":"星期只能是 1 到 5（周六周日没有课）"}` + 422 |
| 时间倒置 | `{"detail":"结束时间必须晚于开始时间"}` + 422 |

## 备注

- `data/app.db` **不进仓库**：每次启动自动建表，演示前删掉就是干净库。
- 测试用的是内存数据库（`tests/test_courses.py`），跑一次不碰 `data/app.db`。
- 接口清单和字段名以 `docs/API.md` 为准。
