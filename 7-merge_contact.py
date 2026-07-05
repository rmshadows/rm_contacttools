#!/usr/bin/env python3
"""按 contacts.id 合并联系人。

默认「交互模式」：字段/号码逐项选择保留哪侧。
「简单模式」：--keep 侧为主，空字段互补，电话/邮箱并集。
"""

import sys
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.ops.merge import merge_contacts
from contacttools.ops.merge_interactive import merge_contacts_interactive
from contacttools.store.database import Database

# ========== 配置（按需修改）==========
DB_PATH = ROOT / "data" / "contacts.sqlite"

KEEP_ID = "8b89c85f-5923-44ca-8569-fd605dc5b935"
DROP_IDS: list[str] = [
    # "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "d996fad2-d79f-44b7-9075-d7be9e677999"
]

# interactive — 逐项选择（默认）
# simple     — 自动规则：keep 优先，空则补，号码/邮箱并集
MERGE_MODE: Literal["interactive", "simple"] = "interactive"

REQUIRE_CONFIRM = True
# =====================================


def _parse_args(argv: list[str]) -> tuple[str, list[str], str]:
    keep = ""
    drop: list[str] = []
    mode = MERGE_MODE
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--keep", "-k") and i + 1 < len(argv):
            keep = argv[i + 1].strip()
            i += 2
            continue
        if arg in ("--drop", "-d") and i + 1 < len(argv):
            i += 1
            while i < len(argv) and not argv[i].startswith("-"):
                drop.append(argv[i].strip())
                i += 1
            continue
        if arg == "--simple":
            mode = "simple"
            i += 1
            continue
        if arg == "--interactive":
            mode = "interactive"
            i += 1
            continue
        i += 1
    return keep, [d for d in drop if d], mode


def main() -> int:
    print("=" * 50)
    print("合并联系人")
    print("=" * 50)
    print(f"数据库: {DB_PATH}")

    if not DB_PATH.exists():
        print("数据库不存在。请先运行  1-import_vcf.py")
        return 1

    keep_id, drop_ids, mode = _parse_args(sys.argv[1:])
    if not keep_id:
        keep_id = KEEP_ID.strip()
    if not drop_ids:
        drop_ids = [d.strip() for d in DROP_IDS if d.strip()]

    if not keep_id or not drop_ids:
        print()
        print("请配置 KEEP_ID / DROP_IDS，或：")
        print("  python 7-merge_contact.py --keep <id> --drop <id> [<id> ...]")
        print("  python 7-merge_contact.py --simple ...   # 简单模式")
        print("  python 7-merge_contact.py --interactive ...  # 交互模式（默认）")
        return 1

    drop_ids = [d for d in drop_ids if d != keep_id]
    if not drop_ids:
        print("DROP_IDS 不能为空（且不能与 KEEP_ID 相同）。")
        return 1

    mode_label = "交互" if mode == "interactive" else "简单"
    print(f"模式: {mode_label}")
    print(f"保留: {keep_id[:8]}…")
    print(f"合并并删除: {len(drop_ids)} 条")
    print()

    merge_fn = (
        merge_contacts_interactive
        if mode == "interactive"
        else merge_contacts
    )

    try:
        with Database(DB_PATH) as db:
            db.init_schema()
            kept = merge_fn(
                db, keep_id, drop_ids, require_confirm=REQUIRE_CONFIRM
            )
            total = db.count_contacts()
    except RuntimeError as e:
        print(e)
        return 0
    except ValueError as e:
        print(f"错误: {e}")
        return 1

    phones = ", ".join(p.number for p in kept.phones if p.number) or "(无)"
    print()
    print(f"已合并到: {kept.fn}  (id {kept.id[:8]}…)")
    print(f"号码: {phones}")
    print(f"库内合计: {total} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
