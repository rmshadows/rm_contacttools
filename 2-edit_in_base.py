#!/usr/bin/env python3
"""步骤 2：在 LibreOffice Base 中可视化编辑联系人（本脚本打印指引并显示当前状态）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.store.database import Database

# ========== 配置 ==========
DB_PATH = ROOT / "data" / "contacts.sqlite"
DOCS_PATH = ROOT / "docs" / "base-setup.md"
# ==========================


def main() -> int:
    print("=" * 50)
    print("步骤 2 / 4  LibreOffice Base 可视化整理")
    print("=" * 50)

    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        print("请先运行  1-import_vcf.py")
        return 1

    with Database(DB_PATH) as db:
        db.init_schema()
        total = db.count_contacts()
        dups = db.duplicate_phone_report()

    print(f"当前库内联系人: {total} 条")
    print(f"重复号码组: {len(dups)} 组")
    print()
    print("【操作说明】")
    print("1. 打开 LibreOffice Base，连接 SQLite（JDBC）")
    print("2. 连接 URL（复制下面整行，按你的实际路径核对）:")
    print()
    print(f"   jdbc:sqlite:{DB_PATH.resolve()}")
    print()
    print("3. JDBC 驱动类:  org.sqlite.JDBC")
    print("   （驱动 jar 安装方法见 docs/base-setup.md）")
    print()
    print("4. 在 Base 里推荐打开这些表/视图:")
    print("   - v_contacts_wide          一行一人，tel1～tel5")
    print("   - v_contacts_full          全部号码/邮箱")
    print("   - v_duplicate_phone_detail 重复号码明细")
    print("   - contacts + phones        改详细字段、增减号码")
    print()
    print("5. 编辑完成后保存，关闭 Base")
    print()
    print("【注意】")
    print("- 不要修改 contacts 表的 id 列")
    print("- 改完 Base 并关闭后，再运行后续脚本")
    print()
    print(f"详细说明: {DOCS_PATH.resolve()}")
    print()
    print("若用 DBeaver → 运行  2-edit_in_dbeaver.py")
    print("下一步 → 运行  3-dedup.py  检查并合并重复联系人")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
