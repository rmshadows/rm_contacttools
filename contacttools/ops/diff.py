from __future__ import annotations

import copy

from contacttools.models.contact import Contact, Email, Phone


def _phone_key(phone: Phone) -> tuple:
    return (phone.number, tuple(sorted(phone.types)), phone.pref)


def _email_key(email: Email) -> tuple:
    return (email.address.lower(), tuple(sorted(email.types)))


def contacts_semantically_equal(a: Contact, b: Contact) -> bool:
    """比较联系人内容（不含 id、时间戳、source）。"""
    if (a.fn or "") != (b.fn or ""):
        return False
    if (a.n_family or "") != (b.n_family or ""):
        return False
    if (a.n_given or "") != (b.n_given or ""):
        return False
    if (a.org or "") != (b.org or ""):
        return False
    if (a.title or "") != (b.title or ""):
        return False
    if (a.note or "") != (b.note or ""):
        return False
    if (a.url or "") != (b.url or ""):
        return False
    if a.photo != b.photo:
        return False
    a_phones = sorted(_phone_key(p) for p in a.phones if p.number)
    b_phones = sorted(_phone_key(p) for p in b.phones if p.number)
    if a_phones != b_phones:
        return False
    a_emails = sorted(_email_key(e) for e in a.emails if e.address)
    b_emails = sorted(_email_key(e) for e in b.emails if e.address)
    return a_emails == b_emails


def find_identical_contact(db, contact: Contact) -> Contact | None:
    for existing in db.list_contacts():
        if contacts_semantically_equal(contact, existing):
            return existing
    return None


def _phones_str(contact: Contact) -> str:
    nums = [p.number for p in contact.phones if p.number]
    return ", ".join(nums) if nums else "(无号码)"


def diff_contact_fields(before: Contact, after: Contact) -> list[str]:
    lines: list[str] = []
    if before.fn != after.fn:
        lines.append(f"  FN: {before.fn!r} → {after.fn!r}")
    if (before.org or "") != (after.org or ""):
        lines.append(f"  ORG: {before.org!r} → {after.org!r}")
    if (before.note or "") != (after.note or ""):
        lines.append(f"  NOTE: {before.note!r} → {after.note!r}")
    if (before.url or "") != (after.url or ""):
        lines.append(f"  URL: {before.url!r} → {after.url!r}")

    before_phones = {p.number for p in before.phones if p.number}
    after_phones = {p.number for p in after.phones if p.number}
    added = after_phones - before_phones
    removed = before_phones - after_phones
    if added:
        lines.append(f"  新增号码: {', '.join(sorted(added))}")
    if removed:
        lines.append(f"  删除号码: {', '.join(sorted(removed))}")
    if before.photo != after.photo:
        if after.photo and not before.photo:
            lines.append("  新增头像")
        elif before.photo and not after.photo:
            lines.append("  移除头像")
        else:
            lines.append("  头像变更")
    return lines


def summarize_new(contact: Contact, *, note: str = "") -> str:
    org = f" ORG={contact.org}" if contact.org else ""
    suffix = f"  ({note})" if note else ""
    return f"  + 新增  {contact.fn}{org}  号码: {_phones_str(contact)}{suffix}"


def summarize_delete(contact: Contact) -> str:
    return f"  - 删除  {contact.fn}  号码: {_phones_str(contact)}"


def summarize_update(fn: str, contact_id: str, changes: list[str]) -> str:
    head = f"  ~ 更新  {fn}  (id {contact_id[:8]}…)"
    if not changes:
        return f"{head}\n      (字段无变化，仍将刷新记录)"
    return head + "\n" + "\n".join(changes)


def copy_contact(contact: Contact) -> Contact:
    return copy.deepcopy(contact)
