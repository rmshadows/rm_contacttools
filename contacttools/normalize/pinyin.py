from __future__ import annotations

import re

from pypinyin import Style, lazy_pinyin

from contacttools.models.contact import Contact

_SPACE_RE = re.compile(r"\s+")


def normalize_pinyin_key(raw: str) -> str:
    """统一拼音排序键：小写、去空白。"""
    return _SPACE_RE.sub("", raw.strip().lower())


def name_to_pinyin(name: str) -> str:
    """将姓名转为拼音排序键（无声调、连写）。"""
    text = name.strip()
    if not text:
        return ""
    parts = lazy_pinyin(text, style=Style.NORMAL, errors="default")
    return normalize_pinyin_key("".join(parts))


def fn_pinyin_for_contact(contact: Contact) -> str:
    """优先用 VCF 自带的 SORT-STRING，否则从 fn 生成。"""
    if contact.sort_string.strip():
        return normalize_pinyin_key(contact.sort_string)
    return name_to_pinyin(contact.fn)


def apply_fn_pinyin(contact: Contact) -> Contact:
    contact.fn_pinyin = fn_pinyin_for_contact(contact)
    return contact
