from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from contacttools.models.contact import Contact
from contacttools.normalize.name import canonical_name, format_warnings
from contacttools.ops.diff import contacts_semantically_equal
from contacttools.ops.name_review import FormatWarningItem, SameNameGroup, find_same_name_groups
from contacttools.store.database import Database


@dataclass
class ExactDuplicateGroup:
    contacts: list[Contact]

    @property
    def keep_id(self) -> str:
        return sorted(c.id for c in self.contacts)[0]

    @property
    def drop_ids(self) -> list[str]:
        return [c.id for c in self.contacts if c.id != self.keep_id]


@dataclass
class PhoneDuplicateGroup:
    number: str
    contacts: list[Contact]


@dataclass
class OtherIssue:
    kind: str
    contact_id: str
    fn: str
    detail: str


@dataclass
class DedupReview:
    exact_groups: list[ExactDuplicateGroup] = field(default_factory=list)
    name_groups: list[SameNameGroup] = field(default_factory=list)
    phone_groups: list[PhoneDuplicateGroup] = field(default_factory=list)
    format_items: list[FormatWarningItem] = field(default_factory=list)
    other_issues: list[OtherIssue] = field(default_factory=list)

    @property
    def needs_attention(self) -> bool:
        return bool(
            self.exact_groups
            or self.name_groups
            or self.phone_groups
            or self.format_items
            or self.other_issues
        )


def find_exact_duplicate_groups(db: Database) -> list[ExactDuplicateGroup]:
    contacts = db.list_contacts()
    groups: list[ExactDuplicateGroup] = []
    used: set[str] = set()

    for i, contact in enumerate(contacts):
        if contact.id in used:
            continue
        group = [contact]
        for other in contacts[i + 1 :]:
            if other.id in used:
                continue
            if contacts_semantically_equal(contact, other):
                group.append(other)
                used.add(other.id)
        if len(group) >= 2:
            groups.append(ExactDuplicateGroup(contacts=group))
            used.add(contact.id)

    return groups


def find_phone_duplicate_groups(db: Database) -> list[PhoneDuplicateGroup]:
    groups: list[PhoneDuplicateGroup] = []
    for row in db.duplicate_phone_report():
        ids = [x for x in row["contact_ids"].split(",") if x]
        contacts = [c for cid in ids if (c := db.get_contact(cid)) is not None]
        if len(contacts) >= 2:
            groups.append(PhoneDuplicateGroup(number=row["number"], contacts=contacts))
    return groups


def find_other_issues(db: Database) -> list[OtherIssue]:
    issues: list[OtherIssue] = []
    for contact in db.list_contacts():
        if not (contact.fn or "").strip():
            issues.append(
                OtherIssue(
                    kind="empty_fn",
                    contact_id=contact.id,
                    fn="(空)",
                    detail="姓名为空，请补全 fn",
                )
            )
        if not contact.phones:
            issues.append(
                OtherIssue(
                    kind="no_phone",
                    contact_id=contact.id,
                    fn=contact.fn or "(空)",
                    detail="无电话号码",
                )
            )
    return issues


def run_dedup_review(db: Database) -> DedupReview:
    format_items: list[FormatWarningItem] = []
    for contact in db.list_contacts():
        messages = format_warnings(contact)
        if messages:
            format_items.append(
                FormatWarningItem(
                    contact_id=contact.id,
                    fn=contact.fn,
                    messages=messages,
                )
            )

    return DedupReview(
        exact_groups=find_exact_duplicate_groups(db),
        name_groups=find_same_name_groups(db),
        phone_groups=find_phone_duplicate_groups(db),
        format_items=format_items,
        other_issues=find_other_issues(db),
    )


def remove_exact_duplicates(
    db: Database, groups: list[ExactDuplicateGroup], *, require_confirm: bool = True
) -> int:
    """删除完全重复条目，每组保留 id 字典序最小的一条。"""
    if not groups:
        return 0

    lines = ["【步骤 1 — 删除完全重复条目】", ""]
    total_drop = 0
    for i, group in enumerate(groups, 1):
        lines.append(f"组 {i}: {group.contacts[0].fn}  保留 {group.keep_id[:8]}…")
        for drop_id in group.drop_ids:
            lines.append(f"  - 删除 id {drop_id[:8]}…")
            total_drop += 1
    lines.append("")
    lines.append(f"共删除 {total_drop} 条重复记录")

    if require_confirm:
        from contacttools.ops.confirm import confirm_or_cancel

        if not confirm_or_cancel("\n".join(lines), "删除完全重复"):
            return 0

    removed = 0
    for group in groups:
        for drop_id in group.drop_ids:
            db.delete_contact(drop_id)
            removed += 1
    return removed


def _sql_quote(value: str) -> str:
    return value.replace("'", "''")


def sql_in_ids(ids: list[str]) -> str:
    if not ids:
        return "('')"
    return "(" + ", ".join(f"'{_sql_quote(i)}'" for i in ids) + ")"


def dbeaver_block(title: str, sql_lines: list[str], actions: list[str]) -> str:
    parts = [f"  [{title}]", "  SQL（DBeaver → SQL 编辑器 → 粘贴 → Ctrl+Enter）："]
    for line in sql_lines:
        parts.append(f"    {line}")
    parts.append("  操作：")
    for action in actions:
        parts.append(f"    · {action}")
    return "\n".join(parts)


def exact_group_sql(group: ExactDuplicateGroup) -> str:
    ids = [c.id for c in group.contacts]
    return dbeaver_block(
        "查看本组",
        [
            f"SELECT id, fn, org, note FROM contacts WHERE id IN {sql_in_ids(ids)};",
            f"SELECT * FROM v_contacts_wide WHERE id IN {sql_in_ids(ids)};",
        ],
        [
            "内容完全一致，任选保留一条即可",
            f"建议保留 id: {group.keep_id}",
            f"删除多余: DELETE FROM contacts WHERE id = '{_sql_quote(group.drop_ids[0])}';"
            if len(group.drop_ids) == 1
            else f"删除多余 id: {', '.join(group.drop_ids)}",
            "DBeaver：contacts 表 → 按 id 筛选 → 选中多余行 → 删除 → Ctrl+S",
            "步骤 1 运行本脚本时可选 y 自动删除完全重复",
        ],
    )


def name_group_sql(group: SameNameGroup) -> str:
    fn = _sql_quote(group.contacts[0].fn)
    ids = [c.id for c in group.contacts]
    return dbeaver_block(
        "查看同名组",
        [
            f"SELECT id, fn, org, note FROM contacts WHERE fn = '{fn}' COLLATE NOCASE;",
            f"SELECT * FROM v_contacts_wide WHERE id IN {sql_in_ids(ids)};",
        ],
        [
            "同一人 → merge 保留一条："
            f"python -m contacttools merge --keep <id> --drop <id2>",
            "不同人 → 保留两条，改其中一人 fn（如加单位后缀）："
            f"UPDATE contacts SET fn = '姓名（备注）' WHERE id = '...';",
            "DBeaver：contacts 表 → 筛选 id → 双击改 fn 或删行",
        ],
    )


def phone_group_sql(group: PhoneDuplicateGroup) -> str:
    num = _sql_quote(group.number)
    ids = [c.id for c in group.contacts]
    return dbeaver_block(
        f"查看号码 {group.number}",
        [
            f"SELECT * FROM v_duplicate_phones WHERE number = '{num}';",
            "SELECT c.id, c.fn, c.org, p.number, p.types "
            f"FROM contacts c JOIN phones p ON p.contact_id = c.id "
            f"WHERE p.number = '{num}';",
            f"SELECT * FROM v_contacts_wide WHERE id IN {sql_in_ids(ids)};",
        ],
        [
            "同一人重复录入 → merge："
            "python -m contacttools merge --keep <id> --drop <id2>",
            "不同人共号（极少）→ 保留两条并改 fn 区分，或删错的那条",
            "DBeaver：phones 表按 number 筛选 → 对照 contact_id 在 contacts 表处理",
        ],
    )


def format_item_sql(item: FormatWarningItem) -> str:
    cid = _sql_quote(item.contact_id)
    return dbeaver_block(
        "姓名格式",
        [
            f"SELECT id, fn, n_family, n_given, org FROM contacts WHERE id = '{cid}';",
        ],
        [
            "统一 fn 为全名；n_given 与 fn 一致，n_family 留空",
            f"UPDATE contacts SET fn = '全名', n_given = '全名', n_family = '' "
            f"WHERE id = '{cid}';",
        ],
    )


def other_issue_sql(issue: OtherIssue) -> str:
    cid = _sql_quote(issue.contact_id)
    return dbeaver_block(
        issue.kind,
        [f"SELECT * FROM v_contacts_wide WHERE id = '{cid}';"],
        [issue.detail, "补全后 Ctrl+S 保存"],
    )


def write_dedup_report(review: DedupReview, path: Path) -> None:
    lines: list[str] = [
        "ContactTools 去重审阅报告",
        "=" * 50,
        "处理顺序建议：",
        "  步骤 1  完全相同的条目 → 删多余，保留一条",
        "  步骤 2  姓名相同、内容不同 → 人工 merge 或改 fn 区分",
        "  步骤 3  电话号码相同 → 人工 merge 或删错条",
        "  步骤 4  格式与其它问题 → 在 DBeaver 修正",
        "",
        f"步骤 1  完全重复: {len(review.exact_groups)} 组",
        f"步骤 2  同名待确认: {len(review.name_groups)} 组",
        f"步骤 3  重复号码: {len(review.phone_groups)} 组",
        f"步骤 4  格式警告: {len(review.format_items)} 条，其它: {len(review.other_issues)} 条",
        "",
    ]

    if review.exact_groups:
        lines.append("=" * 50)
        lines.append("【步骤 1】完全相同的条目")
        lines.append("")
        for i, group in enumerate(review.exact_groups, 1):
            lines.append(f"--- 组 {i}: {group.contacts[0].fn} ---")
            for c in group.contacts:
                phones = ", ".join(p.number for p in c.phones) or "(无)"
                lines.append(f"  id: {c.id}  号码: {phones}")
            lines.append(f"  建议保留: {group.keep_id}")
            lines.append(f"  可删: {', '.join(group.drop_ids)}")
            lines.append(exact_group_sql(group))
            lines.append("")

    if review.name_groups:
        lines.append("=" * 50)
        lines.append("【步骤 2】姓名相同（内容不完全相同）")
        lines.append("")
        for i, group in enumerate(review.name_groups, 1):
            lines.append(f"--- 组 {i}: {group.contacts[0].fn}  [{group.risk}] ---")
            lines.append(f"  {group.hint}")
            for c in group.contacts:
                phones = ", ".join(p.number for p in c.phones) or "(无)"
                lines.append(f"  id: {c.id}  ORG={c.org or ''}  号码: {phones}")
            lines.append(name_group_sql(group))
            lines.append("")

    if review.phone_groups:
        lines.append("=" * 50)
        lines.append("【步骤 3】电话号码相同")
        lines.append("")
        for i, group in enumerate(review.phone_groups, 1):
            lines.append(f"--- 组 {i}: 号码 {group.number} ---")
            for c in group.contacts:
                lines.append(f"  id: {c.id}  FN={c.fn}  ORG={c.org or ''}")
            lines.append(phone_group_sql(group))
            lines.append("")

    if review.format_items or review.other_issues:
        lines.append("=" * 50)
        lines.append("【步骤 4】格式与其它")
        lines.append("")
        for item in review.format_items:
            lines.append(f"  id: {item.contact_id}  FN={item.fn}")
            for msg in item.messages:
                lines.append(f"    ! {msg}")
            lines.append(format_item_sql(item))
            lines.append("")
        for issue in review.other_issues:
            lines.append(f"  id: {issue.contact_id}  {issue.detail}")
            lines.append(other_issue_sql(issue))
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def review_summary_text(review: DedupReview) -> str:
    return "\n".join(
        [
            f"步骤 1  完全重复: {len(review.exact_groups)} 组",
            f"步骤 2  同名待确认: {len(review.name_groups)} 组",
            f"步骤 3  重复号码: {len(review.phone_groups)} 组",
            f"步骤 4  格式/其它: {len(review.format_items) + len(review.other_issues)} 条",
        ]
    )
