"""重置数据库：删掉 data/app.db，重建一个空库（有表结构、没有数据）。

用法（在项目根目录）：
    python scripts/reset_db.py          # 先问一句，输入 y 才动手
    python scripts/reset_db.py --yes    # 不问，直接删（给自动化用）

什么时候用：
- 演示前想从"干净的空库"开始（TEAM.md §4.2 建议演示前做一次）
- 数据灌乱了，想推倒重来

删完再跑 python scripts/seed.py 就能灌回 19 条课表 + 固定事件。
"""

import argparse
import sys
from pathlib import Path

# 把项目根目录放进导入路径：不管在哪个目录执行，都能 import app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import DB_PATH, create_db_and_tables  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="删除 data/app.db 并重建空库")
    parser.add_argument("--yes", action="store_true", help="跳过确认，直接删除")
    args = parser.parse_args()

    if DB_PATH.exists():
        if not args.yes:
            answer = input(f"确定要删除 {DB_PATH} 吗？输入 y 继续：")
            if answer.strip().lower() != "y":
                print("已取消，什么都没删。")
                return 0
        DB_PATH.unlink()
        print(f"旧数据库已删除：{DB_PATH}")
    else:
        print(f"数据库本来就不存在：{DB_PATH}")

    create_db_and_tables()
    print("已重建空库（只有表结构，没有数据）。")
    print("下一步：python scripts/seed.py 灌入演示数据")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
