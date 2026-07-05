#!/usr/bin/env python3
"""步骤 2（DBeaver）：在 DBeaver CE 中可视化编辑联系人。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.store.database import Database

# ========== 配置 ==========
DB_PATH = ROOT / "data" / "contacts.sqlite"
DOCS_PATH = ROOT / "docs" / "dbeaver-setup.md"

# 移动硬盘：设为 True 时打印软链接命令（DBeaver 里固定连 ~/ContactTools-contacts.sqlite）
USE_HOME_SYMLINK = False
SYMLINK_PATH = Path.home() / "ContactTools-contacts.sqlite"
# ==========================


def main() -> int:
    print("=" * 50)
    print("步骤 2 / 4  DBeaver CE 可视化整理")
    print("=" * 50)

    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        print("请先运行  1-import_vcf.py")
        return 1

    with Database(DB_PATH) as db:
        db.init_schema()
        updated = db.backfill_fn_pinyin()
        total = db.count_contacts()
        dups = db.duplicate_phone_report()

    db_path = DB_PATH.resolve()
    print(f"当前库内联系人: {total} 条")
    if updated:
        print(f"已同步拼音排序列 fn_pinyin: {updated} 条")
    print(f"重复号码组: {len(dups)} 组")
    print()
    print("【DBeaver 连接（首次）】")
    print("1. 数据库 → 新建连接 → SQLite")
    print("2. Path 选下面文件（浏览即可，不用 JDBC）：")
    print()
    print(f"   {db_path}")
    print()
    if USE_HOME_SYMLINK:
        print("【移动硬盘 — 固定路径】插盘后执行：")
        print(f"   ln -sf {db_path} {SYMLINK_PATH}")
        print(f"   DBeaver 里 Path 填: {SYMLINK_PATH}")
        print()
    print("3. 测试连接 → 完成")
    print()
    print("【推荐打开】")
    print("  v_contacts_wide          一行一人（tel1~tel5，快速浏览）")
    print("  v_contacts_full          一行一人（全部号码/邮箱，不限个数）")
    print("  v_duplicate_phone_detail 重复号码明细（每人每条号码一行）")
    print("  v_duplicate_phones       重复号码汇总")
    print("  phones                   增删改号码")
    print("  contacts                 姓名、ORG、NOTE、URL")
    print()
    print("【按拼音排序】SQL 编辑器执行：")
    print("  SELECT fn, fn_pinyin, phones FROM v_contacts_full")
    print("  ORDER BY fn_pinyin COLLATE NOCASE;")
    print("  （改姓名后重新运行本脚本，会同步 fn_pinyin）")
    print()
    print("【查重复号码明细】")
    print("  SELECT * FROM v_duplicate_phone_detail")
    print("  ORDER BY dup_count DESC, fn_pinyin, number;")
    print()
    print("【改完记得】数据视图里 Ctrl+S 提交，再运行 3-dedup.py")
    print()
    print("【注意】不要改 contacts.id；超过 5 个号码请用 v_contacts_full 查看，在 phones 表编辑")
    print()
    print(f"详细说明: {DOCS_PATH.resolve()}")
    print()
    print("下一步 → 运行  3-dedup.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
