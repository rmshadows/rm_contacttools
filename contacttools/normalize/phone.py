from __future__ import annotations

import re

_DIGITS_ONLY = re.compile(r"\D")


def normalize_phone(raw: str) -> str:
    """去掉非数字字符，保留前导 0（如 0596 区号）。"""
    if not raw:
        return ""
    number = _DIGITS_ONLY.sub("", raw.strip())
    if number.startswith("86") and len(number) > 11:
        number = number[2:]
    return number


def normalize_contact_phones(contact) -> None:
    for idx, phone in enumerate(contact.phones):
        phone.number = normalize_phone(phone.number)
        phone.sort_order = idx
    contact.phones = [p for p in contact.phones if p.number]
