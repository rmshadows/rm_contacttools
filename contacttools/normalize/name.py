from __future__ import annotations

import re
from typing import Literal

from contacttools.models.contact import Contact

NameMode = Literal["split", "fullname"]

_SPACE_RE = re.compile(r"\s+")


def composed_name(contact: Contact) -> str:
    """姓 + 名。"""
    return (contact.n_family or "") + (contact.n_given or "")


def normalize_to_fullname(contact: Contact) -> Contact:
    """
    fullname 模式：不解析姓氏。
    fn = VCF 的 FN；n_family 留空；n_given = fn（整段显示名）。
    """
    raw = contact.fn.strip()
    if not raw:
        raw = composed_name(contact).strip()
    if not raw:
        raw = (contact.n_given or "").strip()

    contact.fn = raw
    contact.n_family = ""
    contact.n_given = raw
    return contact


def normalize_split_name(contact: Contact) -> Contact:
    """
    split 模式：解析姓氏。
    fn 保留 VCF 的 FN；N 字段分别写入 n_family（姓）、n_given（名）。
    """
    family = (contact.n_family or "").strip()
    given = (contact.n_given or "").strip()
    fn = contact.fn.strip()

    if family and given:
        contact.n_family = family
        contact.n_given = given
        if not fn:
            contact.fn = composed_name(contact)
    elif given and not family:
        contact.n_family = ""
        contact.n_given = given
        if not fn:
            contact.fn = given
    elif fn:
        contact.n_family = ""
        contact.n_given = fn
    else:
        contact.n_family = family
        contact.n_given = given
        if not fn and (family or given):
            contact.fn = composed_name(contact) or given

    return contact


def normalize_name(contact: Contact, mode: NameMode = "fullname") -> Contact:
    if mode == "split":
        return normalize_split_name(contact)
    return normalize_to_fullname(contact)


def canonical_name(contact: Contact) -> str:
    """用于「同名」分组的规范化键。"""
    raw = _SPACE_RE.sub("", (contact.fn or contact.n_given or "").strip())
    return raw.casefold()


def format_warnings(contact: Contact, *, name_mode: NameMode = "fullname") -> list[str]:
    """姓名格式警告（split 模式下保留姓名字段视为正常）。"""
    warnings: list[str] = []
    if name_mode == "split":
        if not contact.fn.strip() and not (contact.n_given or "").strip():
            warnings.append("姓名为空")
        return warnings

    if contact.n_family:
        warnings.append(
            f"仍含姓字段（应统一为全名）: 姓={contact.n_family!r} FN={contact.fn!r}"
        )
    if contact.fn and contact.n_given and contact.fn.strip() != contact.n_given.strip():
        warnings.append(
            f"FN 与 N 不一致: FN={contact.fn!r} N={contact.n_given!r}"
        )
    if not contact.fn.strip():
        warnings.append("姓名为空")
    return warnings


def phone_set(contact: Contact) -> set[str]:
    return {p.number for p in contact.phones if p.number}


def classify_same_name_group(contacts: list[Contact]) -> tuple[str, str]:
    if len(contacts) < 2:
        return "ok", ""

    sets = [phone_set(c) for c in contacts]
    non_empty = [s for s in sets if s]

    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            if sets[i] & sets[j]:
                return (
                    "phone_overlap",
                    "⚠ 同名且存在相同号码 — 请在「重复号码」里处理，或合并为一人",
                )

    if len(non_empty) >= 2:
        orgs = {c.org or "" for c in contacts}
        if len(orgs) == 1 and "" not in orgs:
            return (
                "likely_same_person",
                "⚠ 同名、号码各不相同，但 ORG 相同 — 可能是同一人多个号码，请核对后手动 merge",
            )
        return (
            "ambiguous",
            "⚠ 同名、号码各不相同 — 可能是同一人，也可能是不同人，请勿自动合并，请人工确认",
        )

    if any(not s for s in sets):
        return (
            "ambiguous",
            "⚠ 同名且有人无号码 — 请补全号码或人工决定是否合并",
        )

    return "ambiguous", "⚠ 同名 — 请人工确认"
