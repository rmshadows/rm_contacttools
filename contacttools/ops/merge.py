from __future__ import annotations

from contacttools.models.contact import Contact, Phone, Email
from contacttools.ops.diff import copy_contact, diff_contact_fields
from contacttools.store.database import Database


def find_duplicate_groups(db: Database) -> list[dict]:
    rows = db.duplicate_phone_report()
    groups: list[dict] = []
    for row in rows:
        ids = row["contact_ids"].split(",")
        contacts = [db.get_contact(cid) for cid in ids]
        contacts = [c for c in contacts if c is not None]
        groups.append(
            {
                "number": row["number"],
                "count": row["contact_count"],
                "contacts": contacts,
            }
        )
    return groups


def _merge_simple_fields(kept: Contact, other: Contact) -> None:
    """简单模式：keep 优先；空字段从 other 补；电话/邮箱取并集。"""
    seen_numbers = {p.number for p in kept.phones}
    order = len(kept.phones)
    for phone in other.phones:
        if phone.number and phone.number not in seen_numbers:
            kept.phones.append(
                Phone(
                    number=phone.number,
                    types=phone.types,
                    pref=phone.pref,
                    sort_order=order,
                )
            )
            seen_numbers.add(phone.number)
            order += 1

    seen_emails = {e.address.lower() for e in kept.emails if e.address}
    order = len(kept.emails)
    for email in other.emails:
        if email.address and email.address.lower() not in seen_emails:
            kept.emails.append(
                Email(
                    address=email.address,
                    types=email.types,
                    sort_order=order,
                )
            )
            seen_emails.add(email.address.lower())
            order += 1

    if not kept.org and other.org:
        kept.org = other.org
    if not kept.note and other.note:
        kept.note = other.note
    if not kept.url and other.url:
        kept.url = other.url
    if not kept.photo and other.photo:
        kept.photo = other.photo


def simulate_merge(
    db: Database, keep_id: str, drop_ids: list[str]
) -> tuple[Contact, list[tuple[str, str]], list[str]]:
    """模拟合并，不写库。返回 (合并后的副本, [(删除名, id), ...], 变更说明)。"""
    kept = db.get_contact(keep_id)
    if kept is None:
        raise ValueError(f"找不到联系人: {keep_id}")

    kept_copy = copy_contact(kept)
    before = copy_contact(kept_copy)
    deleted: list[tuple[str, str]] = []

    for drop_id in drop_ids:
        if drop_id == keep_id:
            continue
        other = db.get_contact(drop_id)
        if other is None:
            continue
        deleted.append((other.fn, drop_id))
        _merge_simple_fields(kept_copy, other)

        changes = diff_contact_fields(before, kept_copy)
    return kept_copy, deleted, changes


def merge_contacts(
    db: Database,
    keep_id: str,
    drop_ids: list[str],
    *,
    require_confirm: bool = True,
) -> Contact:
    from contacttools.ops.confirm import confirm_or_cancel
    from contacttools.ops.plan import build_merge_plan

    if require_confirm:
        plan = build_merge_plan(db, keep_id, drop_ids)
        if not confirm_or_cancel(plan.as_text(), "合并联系人"):
            raise RuntimeError("用户取消操作，数据库未修改")

    kept = db.get_contact(keep_id)
    if kept is None:
        raise ValueError(f"找不到联系人: {keep_id}")

    for drop_id in drop_ids:
        if drop_id == keep_id:
            continue
        other = db.get_contact(drop_id)
        if other is None:
            continue

        _merge_simple_fields(kept, other)

        db.merge_history_snapshot(keep_id, other)
        db.delete_contact(drop_id)

    kept.touch()
    db.save_contact(kept)
    return kept
