from __future__ import annotations

from contacttools.models.contact import Contact


def merge_contact_fields(existing: Contact, incoming: Contact) -> Contact:
    """upsert 模式：保留 existing.id，按字段合并 incoming。"""
    existing.fn = incoming.fn or existing.fn
    existing.n_family = incoming.n_family or existing.n_family or ""
    existing.n_given = incoming.n_given or existing.n_given or existing.fn
    existing.org = incoming.org or existing.org
    existing.title = incoming.title if incoming.title is not None else existing.title
    existing.note = incoming.note or existing.note
    existing.url = incoming.url or existing.url
    if incoming.photo:
        existing.photo = incoming.photo

    seen = {p.number for p in existing.phones}
    order = len(existing.phones)
    for phone in incoming.phones:
        if phone.number not in seen:
            phone.sort_order = order
            existing.phones.append(phone)
            seen.add(phone.number)
            order += 1

    seen_emails = {e.address for e in existing.emails}
    order = len(existing.emails)
    for email in incoming.emails:
        if email.address not in seen_emails:
            email.sort_order = order
            existing.emails.append(email)
            seen_emails.add(email.address)
            order += 1

    existing.source = incoming.source or existing.source
    return existing
