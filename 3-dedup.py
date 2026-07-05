#!/usr/bin/env python3
"""步骤 3：去重审阅（分步提示 + SQL / DBeaver 操作说明）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.ops.dedup_review import (
    dbeaver_block,
    exact_group_sql,
    format_item_sql,
    name_group_sql,
    other_issue_sql,
    phone_group_sql,
    remove_exact_duplicates,
    review_summary_text,
    run_dedup_review,
    write_dedup_report,
)
from contacttools.ops.name_review import show_popup_warning
from contacttools.store.database import Database

# ========== 配置 ==========
DB_PATH = ROOT / "data" / "contacts.sqlite"
REPORT_PATH = ROOT / "data" / "review_warnings.txt"

# 步骤 1 发现完全重复时，是否在终端询问并自动删除（保留每组一条）
OFFER_REMOVE_EXACT = True

SHOW_POPUP = True
# ==========================


def _print_contact_line(c) -> None:
    phones = ", ".join(p.number for p in c.phones) or "(无号码)"
    org = c.org or ""
    print(f"  id: {c.id}")
    print(f"  FN={c.fn}  ORG={org}")
    print(f"  号码: {phones}")


def _print_section(title: str, body: str) -> None:
    print("=" * 50)
    print(title)
    print("=" * 50)
    print(body)
    print()


def _print_step_header(n: int, title: str, count: int, unit: str) -> None:
    print("=" * 50)
    print(f"【步骤 {n}】{title} — {count} {unit}")
    print("=" * 50)


def main() -> int:
    print("=" * 50)
    print("步骤 3 / 4  去重审阅")
    print("=" * 50)
    print("建议按顺序处理：")
    print("  1  完全相同的条目 → 删多余")
    print("  2  姓名相同 → merge 或改 fn 区分")
    print("  3  电话相同 → merge 或删错条")
    print("  4  格式与其它 → DBeaver 修正")
    print()

    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        print("请先运行  1-import_vcf.py")
        return 1

    with Database(DB_PATH) as db:
        db.init_schema()
        review = run_dedup_review(db)
        write_dedup_report(review, REPORT_PATH)
        summary = review_summary_text(review)

        if not review.needs_attention:
            print("未发现需要去重或修正的问题。")
            print()
            print("下一步 → 运行  4-export_vcf.py")
            return 0

        print(summary)
        print(f"完整报告（含 SQL）: {REPORT_PATH.resolve()}")
        print()

        # --- 步骤 1 ---
        if review.exact_groups:
            _print_step_header(1, "完全相同的条目", len(review.exact_groups), "组")
            print("内容完全一致，只需保留每组一条，其余可安全删除。")
            print()
            for i, group in enumerate(review.exact_groups[:8], 1):
                print(f"--- 组 {i}: {group.contacts[0].fn} ---")
                for c in group.contacts:
                    _print_contact_line(c)
                print(f"  建议保留 id: {group.keep_id}")
                print(f"  可删 id:     {', '.join(group.drop_ids)}")
                print(exact_group_sql(group))
                print()
            if len(review.exact_groups) > 8:
                print(f"… 还有 {len(review.exact_groups) - 8} 组，见报告文件")
                print()

            if OFFER_REMOVE_EXACT:
                removed = remove_exact_duplicates(
                    db, review.exact_groups, require_confirm=True
                )
                if removed:
                    print(f"已删除 {removed} 条完全重复记录。")
                    review = run_dedup_review(db)
                    write_dedup_report(review, REPORT_PATH)
                    print()

        # --- 步骤 2 ---
        if review.name_groups:
            _print_step_header(2, "姓名相同（内容不完全相同）", len(review.name_groups), "组")
            print("请判断是同一人还是不同人。程序不会自动合并。")
            print()
            for i, group in enumerate(review.name_groups[:8], 1):
                print(f"--- 组 {i}: {group.contacts[0].fn}  [{group.risk}] ---")
                print(f"  {group.hint}")
                for c in group.contacts:
                    _print_contact_line(c)
                print(name_group_sql(group))
                print("  命令行 merge 示例:")
                ids = [c.id for c in group.contacts]
                print(
                    f"    python -m contacttools merge --keep {ids[0]} --drop {ids[1]}"
                )
                print()
            if len(review.name_groups) > 8:
                print(f"… 还有 {len(review.name_groups) - 8} 组，见报告文件")
                print()

        # --- 步骤 3 ---
        if review.phone_groups:
            _print_step_header(3, "电话号码相同", len(review.phone_groups), "组")
            print("通常为同一人重复录入，merge 保留信息更全的一条。")
            print()
            _print_section(
                "全局查看（DBeaver SQL）",
                dbeaver_block(
                    "全部重复号码",
                    ["SELECT * FROM v_duplicate_phones ORDER BY contact_count DESC;"],
                    ["contact_count > 1 的号码需逐步处理"],
                ),
            )
            for i, group in enumerate(review.phone_groups[:8], 1):
                print(f"--- 组 {i}: 号码 {group.number} ---")
                for c in group.contacts:
                    _print_contact_line(c)
                print(phone_group_sql(group))
                ids = [c.id for c in group.contacts]
                if len(ids) >= 2:
                    print(
                        f"  merge 示例: python -m contacttools merge "
                        f"--keep {ids[0]} --drop {ids[1]}"
                    )
                print()
            if len(review.phone_groups) > 8:
                print(f"… 还有 {len(review.phone_groups) - 8} 组，见报告文件")
                print()

        # --- 步骤 4 ---
        step4_count = len(review.format_items) + len(review.other_issues)
        if step4_count:
            _print_step_header(4, "格式与其它", step4_count, "条")

            if review.format_items:
                print("--- 姓名格式 ---")
                for item in review.format_items[:10]:
                    print(f"  ! {item.fn}  (id {item.contact_id[:8]}…)")
                    for msg in item.messages:
                        print(f"      {msg}")
                    print(format_item_sql(item))
                    print()
                if len(review.format_items) > 10:
                    print(f"… 还有 {len(review.format_items) - 10} 条，见报告")
                    print()

            if review.other_issues:
                print("--- 其它 ---")
                for issue in review.other_issues[:10]:
                    print(f"  ! {issue.fn}  id {issue.contact_id[:8]}…  {issue.detail}")
                    print(other_issue_sql(issue))
                    print()

        print("=" * 50)
        print("【DBeaver 常用入口】")
        print("=" * 50)
        print("  连接文件: data/contacts.sqlite")
        print("  浏览全部: SELECT * FROM v_contacts_full ORDER BY fn_pinyin COLLATE NOCASE;")
        print("  重复明细: SELECT * FROM v_duplicate_phone_detail ORDER BY dup_count DESC;")
        print("  按 id 查: SELECT * FROM v_contacts_wide WHERE id IN ('...');")
        print("  改姓名:   contacts 表 → 双击 fn → Ctrl+S")
        print("  删整人:   contacts 表选中行删除（phones 会自动删）")
        print("  加号码:   phones 表底部 + 行，填 contact_id、number、types")
        print()

        if SHOW_POPUP and review.needs_attention:
            show_popup_warning(summary)

        print("处理完成后 → 运行  4-export_vcf.py")
        print("可再次运行本脚本检查是否还有遗留问题。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
