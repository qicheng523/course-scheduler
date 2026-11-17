"""环境自检脚本：一条命令确认 Python 版本和 7 个依赖都装好了。

用法（在项目根目录）：  python scripts/check_env.py
全部显示 [OK] 就说明可以直接启动服务器。
"""

import importlib.util
import sys

# 键是 Python 里的模块名，值是给人看的说明
REQUIRED: dict[str, str] = {
    "fastapi": "FastAPI 框架",
    "uvicorn": "启动网站的服务器",
    "sqlmodel": "数据库表 + 数据模型",
    "jinja2": "HTML 模板引擎",
    "multipart": "表单处理（python-multipart）",
    "pytest": "测试框架",
    "httpx2": "测试客户端的底层依赖",
}


def main() -> int:
    """逐项检查，全部通过返回 0，有缺失返回 1。"""
    print(f"Python 版本：{sys.version.split()[0]}")
    if sys.version_info < (3, 12):
        print("[!!] 需要 Python 3.12 或更高版本")
        return 1

    missing: list[str] = []
    for module, label in REQUIRED.items():
        installed = importlib.util.find_spec(module) is not None
        print(f"[{'OK' if installed else '!!'}] {module:<10} {label}")
        if not installed:
            missing.append(module)

    if missing:
        print("\n有依赖缺失，请执行：pip install -r requirements.txt")
        return 1

    print("\n全部就绪，启动命令：python -m uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
