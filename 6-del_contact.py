#!/usr/bin/env python3
"""按 contacts.id 删除联系人（phones / emails 外键级联删除，无孤儿记录）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.ops.delete_contact import delete_contacts
from contacttools.store.database import Database

# ========== 配置（按需修改）==========
DB_PATH = ROOT / "data" / "contacts.sqlite"

# 要删除的 contacts.id（可填多个）
CONTACT_IDS: list[str] = [
    # "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
]

# 写库前确认
REQUIRE_CONFIRM = True
# =====================================


def main() -> int:
    ids = [a.strip() for a in sys.argv[1:] if a.strip()] if len(sys.argv) > 1 else CONTACT_IDS
    ids = [i for i in ids if i]

    print("=" * 50)
    print("删除联系人")
    print("=" * 50)
    print(f"数据库: {DB_PATH}")

    if not DB_PATH.exists():
        print("数据库不存在。请先运行  1-import_vcf.py")
        return 1

    if not ids:
        print()
        print("请在本脚本顶部 CONTACT_IDS 填入 id，或命令行传入：")
        print("  python 6-del_contact.py <id> [<id> ...]")
        return 1

    print(f"待删 id: {len(ids)} 个")
    print()

    with Database(DB_PATH) as db:
        db.init_schema()
        result = delete_contacts(db, ids, require_confirm=REQUIRE_CONFIRM)

    if result.get("cancelled"):
        print("已取消。数据库未修改。")
        return 0

    if result.get("empty"):
        print("没有可删除的有效 id。")
        if result.get("missing_ids"):
            print("以下 id 不存在:")
            for cid in result["missing_ids"]:
                print(f"  {cid}")
        return 1

    print(f"已删除联系人: {result['deleted']} 条")
    print(f"连带删除 phones: {result['phones_removed']} 条")
    print(f"连带删除 emails: {result['emails_removed']} 条")
    if result.get("missing_ids"):
        print(f"忽略的无效 id: {len(result['missing_ids'])} 个")
    print(f"库内合计: {result['total_in_db']} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
