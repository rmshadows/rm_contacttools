#!/usr/bin/env python3
"""批量新增联系人：从文本文件读取姓名、电话、单位、备注。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.ops.add_contact import (
    add_contacts,
    format_add_preview,
    parse_contacts_file,
    phone_conflicts,
)
from contacttools.ops.confirm import confirm_plan_with_report
from contacttools.store.database import Database

# ========== 配置（按需修改）==========
# 每行：姓名 + 电话（必填），单位 ORG、备注 NOTE（可空）
# 推荐 Tab 分隔；空格分隔时备注可含空格
# 同名多行 → 合并为一人、多个号码
#
# 示例（Tab）：
#   张三	13800138000	某某公司	重要客户
#   张三	13900139000	某某公司	重要客户
# 示例（空格，仅姓名+电话）：
#   李四 059612345678
#
# 空行与 # 开头行会忽略
INPUT_FILE = "input/add_contacts.txt"

DB_PATH = ROOT / "data" / "contacts.sqlite"

REQUIRE_CONFIRM = True
SKIP_IDENTICAL = True
# =====================================


def _terminal_add_summary(contacts, conflicts) -> str:
    lines = [
        "【待新增联系人 — 摘要】",
        f"合计: {len(contacts)} 人",
    ]
    if conflicts:
        lines.append(f"号码冲突: {len(conflicts)} 处（详情见预览文件）")
    lines.append("")
    lines.append("【将新增】")
    max_show = 50
    for idx, contact in enumerate(contacts[:max_show], 1):
        phone = contact.phones[0].number if contact.phones else "(无)"
        org = f"  单位={contact.org}" if contact.org else ""
        note = f"  备注={contact.note}" if contact.note else ""
        lines.append(f"  {idx}. {contact.fn}  {phone}{org}{note}")
    if len(contacts) > max_show:
        lines.append(f"  … 还有 {len(contacts) - max_show} 人，见完整预览文件")
    return "\n".join(lines)


def main() -> int:
    input_path = Path(INPUT_FILE)
    if not input_path.is_absolute():
        input_path = ROOT / input_path

    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])

    print("=" * 50)
    print("批量新增联系人 → SQLite")
    print("=" * 50)
    print(f"输入: {input_path}")
    print(f"数据库: {DB_PATH}")
    print()

    if not input_path.exists():
        print(f"找不到文件: {input_path}")
        print("请创建文本文件，格式见本脚本顶部注释。")
        return 1

    contacts, errors = parse_contacts_file(input_path)

    if errors:
        print("【解析提示】")
        for msg in errors:
            print(f"  {msg}")
        print()

    if not contacts:
        print("没有可写入的联系人。")
        return 1 if errors else 0

    with Database(DB_PATH) as db:
        db.init_schema()
        conflicts: list[dict] = []
        for contact in contacts:
            conflicts.extend(phone_conflicts(db, contact))

        preview = format_add_preview(
            contacts, conflicts, source=str(input_path.resolve())
        )
        preview_path = DB_PATH.parent / "add_contact_preview.txt"

        if REQUIRE_CONFIRM:
            if not confirm_plan_with_report(
                preview,
                _terminal_add_summary(contacts, conflicts),
                preview_path,
                "批量新增联系人",
            ):
                print("已取消。数据库未修改。")
                return 0

        result = add_contacts(db, contacts, skip_identical=SKIP_IDENTICAL)

    print()
    for line in result["details"]:
        print(line)
    print()
    print(f"解析有效: {len(contacts)} 人")
    print(f"写入: {result['saved']} 人")
    print(f"跳过: {result['skipped']} 人")
    if errors:
        print(f"解析提示: {len(errors)} 条")
    print(f"库内合计: {result['total_in_db']} 条")
    print()
    print("下一步 → DBeaver 核对，或运行  3-dedup.py /  4-export_vcf.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
