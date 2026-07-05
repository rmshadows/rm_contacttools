#!/usr/bin/env python3
"""步骤 0：重置数据库，清空所有联系人数据，从头开始。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.ops.reset import reset_database

# ========== 配置 ==========
DB_PATH = ROOT / "data" / "contacts.sqlite"

# 写库前必须确认（改 False 可跳过，不推荐）
REQUIRE_CONFIRM = True

# 是否删除 data/review_warnings.txt 等辅助文件
CLEAR_REPORTS = True
# ==========================


def main() -> int:
    print("=" * 50)
    print("重置 ContactTools 数据库")
    print("=" * 50)
    print()

    result = reset_database(
        DB_PATH,
        require_confirm=REQUIRE_CONFIRM,
        clear_reports=CLEAR_REPORTS,
    )

    if result.get("already_empty"):
        print(f"数据库不存在: {DB_PATH}")
        print("已是空状态。若要初始化表结构，运行: python -m contacttools init")
        return 0

    if result.get("cancelled"):
        print("已取消。数据库未修改。")
        return 0

    print(f"已清空 {result['cleared_contacts']} 条联系人")
    print(f"数据库: {result['db_path']}")
    print(f"当前库内: {result['total_in_db']} 条")
    print()
    print("下一步 → 运行  1-import_vcf.py  重新导入 VCF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
