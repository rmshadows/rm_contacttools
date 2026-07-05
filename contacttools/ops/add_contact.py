from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from contacttools.models.contact import Contact, Phone, new_id
from contacttools.normalize.name import normalize_to_fullname
from contacttools.normalize.phone import normalize_contact_phones
from contacttools.normalize.pinyin import apply_fn_pinyin
from contacttools.ops.diff import find_identical_contact
from contacttools.store.database import Database


@dataclass
class _ContactDraft:
    fn: str
    phones: list[str] = field(default_factory=list)
    phone_set: set[str] = field(default_factory=set)
    org: str | None = None
    note: str | None = None


def build_contact(
    fn: str,
    phones: list[str],
    *,
    org: str | None = None,
    note: str | None = None,
    phone_type: str = "CELL",
) -> Contact | None:
    """从姓名、号码列表、单位、备注构造联系人。"""
    fn = fn.strip()
    if not fn or not phones:
        return None

    contact = Contact(
        fn=fn,
        org=org.strip() or None if org else None,
        note=note.strip() or None if note else None,
        source="manual",
    )
    contact.phones = [
        Phone(
            number=number,
            types=[phone_type or "CELL"],
            pref=(idx == 0),
            sort_order=idx,
        )
        for idx, number in enumerate(phones)
    ]
    normalize_contact_phones(contact)
    if not contact.phones:
        return None
    normalize_to_fullname(contact)
    apply_fn_pinyin(contact)
    contact.id = new_id()
    return contact


def _parse_line_fields(line: str) -> tuple[str, str, str, str] | None:
    """
    解析一行：姓名、电话（必填），单位、备注（可空）。
    推荐 Tab 分隔；也支持空格（备注可含空格）、逗号。
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts: list[str]
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t")]
    elif any(sep in line for sep in (",", "，", ";", "；", "|")):
        for sep in (",", "，", ";", "；", "|"):
            if sep in line:
                parts = [p.strip() for p in line.split(sep)]
                break
        else:
            parts = []
    else:
        parts = line.split(None, 3)

    while len(parts) < 4:
        parts.append("")

    fn, phone, org, note = parts[0], parts[1], parts[2], parts[3]
    if not fn or not phone:
        return None
    return fn, phone, org, note


def parse_contacts_file(path: Path | str) -> tuple[list[Contact], list[str]]:
    """
    从文本批量解析联系人。

    每行：姓名 + 电话（必填），单位 ORG、备注 NOTE（可空）。
    同名多行 → 合并为一人、多个号码。
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    groups: OrderedDict[str, _ContactDraft] = OrderedDict()
    errors: list[str] = []

    for line_no, raw in enumerate(text.splitlines(), 1):
        parsed = _parse_line_fields(raw)
        if parsed is None:
            if raw.strip() and not raw.strip().startswith("#"):
                errors.append(
                    f"第 {line_no} 行格式不对（需「姓名 电话 [单位] [备注]」）: {raw!r}"
                )
            continue

        fn, phone_raw, org_raw, note_raw = parsed
        contact = build_contact(fn, [phone_raw], org=org_raw or None, note=note_raw or None)
        if contact is None:
            errors.append(f"第 {line_no} 行号码无效: {raw!r}")
            continue

        number = contact.phones[0].number
        org = contact.org
        note = contact.note

        if fn not in groups:
            groups[fn] = _ContactDraft(fn=fn)

        draft = groups[fn]
        if number not in draft.phone_set:
            draft.phones.append(number)
            draft.phone_set.add(number)

        if org:
            if draft.org and draft.org != org:
                errors.append(
                    f"第 {line_no} 行单位与同名前几行不一致（保留「{draft.org}」）: {raw!r}"
                )
            elif not draft.org:
                draft.org = org

        if note:
            if draft.note and draft.note != note:
                errors.append(
                    f"第 {line_no} 行备注与同名前几行不一致（保留「{draft.note}」）: {raw!r}"
                )
            elif not draft.note:
                draft.note = note

    contacts: list[Contact] = []
    for draft in groups.values():
        contact = build_contact(
            draft.fn,
            draft.phones,
            org=draft.org,
            note=draft.note,
        )
        if contact is None:
            errors.append(f"合并后联系人无效: {draft.fn!r}")
            continue
        contacts.append(contact)

    return contacts, errors


def phone_conflicts(db: Database, contact: Contact) -> list[dict]:
    """号码已被其他联系人使用时返回冲突列表。"""
    conflicts: list[dict] = []
    seen: set[str] = set()
    for phone in contact.phones:
        if not phone.number or phone.number in seen:
            continue
        seen.add(phone.number)
        for contact_id in db.find_contact_ids_by_phone(phone.number):
            existing = db.get_contact(contact_id)
            if existing is None:
                continue
            conflicts.append(
                {
                    "number": phone.number,
                    "existing_id": existing.id,
                    "existing_fn": existing.fn,
                    "existing_org": existing.org or "",
                }
            )
    return conflicts


def _phones_label(contact: Contact) -> str:
    nums = [p.number for p in contact.phones if p.number]
    return ", ".join(nums) if nums else "(无)"


def format_add_preview(
    contacts: list[Contact],
    conflicts: list[dict],
    *,
    source: str = "",
) -> str:
    lines = ["【待新增联系人】"]
    if source:
        lines.append(f"来源: {source}")
    lines.append("")
    for idx, contact in enumerate(contacts, 1):
        org = contact.org or ""
        note = contact.note or ""
        extra = []
        if org:
            extra.append(f"单位={org}")
        if note:
            extra.append(f"备注={note}")
        suffix = f"  ({', '.join(extra)})" if extra else ""
        lines.append(f"  {idx}. {contact.fn}  {_phones_label(contact)}{suffix}")
    lines.append("")
    lines.append(f"合计: {len(contacts)} 人")

    if conflicts:
        lines.append("")
        lines.append("【号码冲突警告】以下号码已在库中（仍将写入新联系人）：")
        for row in conflicts:
            org = f" ({row['existing_org']})" if row["existing_org"] else ""
            lines.append(
                f"  · {row['number']} → {row['existing_fn']}{org}  id={row['existing_id'][:8]}…"
            )
    return "\n".join(lines)


def add_contacts(
    db: Database,
    contacts: list[Contact],
    *,
    skip_identical: bool = True,
) -> dict:
    saved = 0
    skipped = 0
    details: list[str] = []

    for contact in contacts:
        if skip_identical and find_identical_contact(db, contact):
            skipped += 1
            details.append(f"跳过（已存在相同记录）: {contact.fn}")
            continue
        db.save_contact(contact)
        saved += 1
        details.append(f"已写入: {contact.fn}  {_phones_label(contact)}")

    return {
        "saved": saved,
        "skipped": skipped,
        "total_in_db": db.count_contacts(),
        "details": details,
    }
