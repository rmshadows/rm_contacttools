from __future__ import annotations

import base64
from pathlib import Path

from contacttools.models.contact import Contact, Email, Phone
from contacttools.vcf import template
from contacttools.vcf.fold import fold_line


def _format_n(contact: Contact) -> str:
    """N 字段：有姓则 N:姓;名;;;，否则 N:;全名;;;。"""
    if contact.n_family:
        return f"N:{contact.n_family};{contact.n_given or ''};;;"
    name = contact.fn or contact.n_given or ""
    return f"N:;{name};;;"


def _format_tel(phone: Phone) -> str:
    types = phone.types or ["CELL"]
    number = phone.number
    if phone.pref and len(types) == 1:
        return f"TEL;TYPE={types[0]},PREF=1:{number}"
    if len(types) == 1:
        return f"TEL;TYPE={types[0]}:{number}"
    joined = ";".join(types)
    return f'TEL;TYPE="{joined}":{number}'


def _format_email(email: Email) -> str:
    types = email.types or ["HOME"]
    if len(types) == 1:
        return f"EMAIL;TYPE={types[0]}:{email.address}"
    joined = ";".join(types)
    return f'EMAIL;TYPE="{joined}":{email.address}'


def _format_photo(photo: bytes) -> list[str]:
    encoded = base64.b64encode(photo).decode("ascii")
    line = f"PHOTO:data:{template.PHOTO_MIME};base64,{encoded}"
    return fold_line(line, template.MAX_LINE_LENGTH)


def contact_to_lines(contact: Contact) -> list[str]:
    lines = [
        "BEGIN:VCARD",
        f"VERSION:{template.VERSION}",
        f"PRODID:{template.PRODID}",
        f"FN:{contact.fn}",
        _format_n(contact),
    ]

    for phone in sorted(contact.phones, key=lambda p: p.sort_order):
        if phone.number:
            lines.append(_format_tel(phone))

    if contact.note:
        lines.append(f"NOTE:{contact.note}")

    if contact.url:
        lines.append(f"URL:{contact.url}")

    if contact.org is not None:
        lines.append(f"ORG:{contact.org}")
        title = contact.title if contact.title is not None else ""
        lines.append(f"TITLE:{title}")

    for email in sorted(contact.emails, key=lambda e: e.sort_order):
        if email.address:
            lines.append(_format_email(email))

    if contact.photo:
        lines.extend(_format_photo(contact.photo))

    lines.append("END:VCARD")
    return lines


def contacts_to_vcf_text(contacts: list[Contact]) -> str:
    chunks: list[str] = []
    for contact in contacts:
        chunks.extend(contact_to_lines(contact))
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def write_vcf_file(contacts: list[Contact], path: Path | str) -> None:
    path = Path(path)
    path.write_text(contacts_to_vcf_text(contacts), encoding="utf-8")
