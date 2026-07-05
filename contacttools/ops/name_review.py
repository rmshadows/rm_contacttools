from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from contacttools.models.contact import Contact
from contacttools.normalize.name import (
    canonical_name,
    classify_same_name_group,
    format_warnings,
    phone_set,
)
from contacttools.store.database import Database


@dataclass
class FormatWarningItem:
    contact_id: str
    fn: str
    messages: list[str]


@dataclass
class SameNameGroup:
    canonical: str
    risk: str
    hint: str
    contacts: list[Contact]


def find_format_warning_items(db: Database) -> list[FormatWarningItem]:
    items: list[FormatWarningItem] = []
    for contact in db.list_contacts():
        messages = format_warnings(contact)
        if messages:
            items.append(
                FormatWarningItem(
                    contact_id=contact.id,
                    fn=contact.fn,
                    messages=messages,
                )
            )
    return items


def find_same_name_groups(db: Database) -> list[SameNameGroup]:
    by_name: dict[str, list[Contact]] = {}
    for contact in db.list_contacts():
        key = canonical_name(contact)
        if not key:
            continue
        by_name.setdefault(key, []).append(contact)

    groups: list[SameNameGroup] = []
    for key, contacts in sorted(by_name.items(), key=lambda x: x[0]):
        if len(contacts) < 2:
            continue
        risk, hint = classify_same_name_group(contacts)
        if risk == "phone_overlap":
            continue
        groups.append(
            SameNameGroup(
                canonical=key,
                risk=risk,
                hint=hint,
                contacts=contacts,
            )
        )
    return groups


def run_full_review(db: Database) -> dict:
    phone_dupes = db.duplicate_phone_report()
    format_items = find_format_warning_items(db)
    name_groups = find_same_name_groups(db)
    return {
        "phone_duplicate_groups": len(phone_dupes),
        "format_warnings": len(format_items),
        "same_name_groups": len(name_groups),
        "format_items": format_items,
        "name_groups": name_groups,
        "phone_dupes": phone_dupes,
    }


def write_review_report(review: dict, path: Path) -> None:
    lines: list[str] = [
        "ContactTools 人工审阅报告",
        "=" * 50,
        f"重复号码组: {review['phone_duplicate_groups']}",
        f"姓名格式警告: {review['format_warnings']} 条",
        f"同名待确认组: {review['same_name_groups']} 组",
        "",
    ]

    if review["format_items"]:
        lines.append("【一、姓名格式不统一 — 请逐条核对】")
        lines.append("")
        for item in review["format_items"]:
            lines.append(f"  id: {item.contact_id}")
            lines.append(f"  FN: {item.fn}")
            for msg in item.messages:
                lines.append(f"    ! {msg}")
            lines.append("")

    if review["name_groups"]:
        lines.append("【二、同名不同记录 — 请人工决定是否 merge】")
        lines.append("（程序不会自动合并同名）")
        lines.append("")
        for i, group in enumerate(review["name_groups"], 1):
            lines.append(f"--- 同名组 {i}: {group.contacts[0].fn} ({group.risk}) ---")
            lines.append(f"  {group.hint}")
            for c in group.contacts:
                phones = ", ".join(p.number for p in c.phones) or "(无号码)"
                org = c.org or ""
                fam = c.n_family or ""
                given = c.n_given or ""
                lines.append(f"  id: {c.id}")
                lines.append(f"      FN={c.fn}  姓={fam} 名={given}  ORG={org}")
                lines.append(f"      号码: {phones}")
            lines.append("  → merge 示例: python -m contacttools merge --keep <id> --drop <id2>")
            lines.append("")

    if review["phone_dupes"]:
        lines.append("【三、重复号码 — 高置信度可合并】")
        lines.append("")
        for row in review["phone_dupes"]:
            lines.append(f"  号码 {row['number']}: {row['contact_count']} 人  ids={row['contact_ids']}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def review_summary_text(review: dict) -> str:
    parts = [
        f"重复号码: {review['phone_duplicate_groups']} 组",
        f"姓名格式警告: {review['format_warnings']} 条",
        f"同名待确认: {review['same_name_groups']} 组",
    ]
    if review["format_warnings"] or review["same_name_groups"] or review["phone_duplicate_groups"]:
        parts.append("\n请打开 data/review_warnings.txt 查看详情并在 DBeaver 中修正。")
    else:
        parts.append("\n未发现需要人工处理的问题。")
    return "\n".join(parts)


def show_popup_warning(summary: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showwarning("ContactTools 去重提醒", summary)
        root.destroy()
    except Exception:
        pass
