from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Optional

from contacttools.models.contact import Contact, Email, Phone
from contacttools.vcf.fold import unfold_lines

_PARAM_RE = re.compile(r"^([^;:]+)(?:;(.*))?$")
_PHOTO_DATA_URI = re.compile(
    r"^PHOTO(?:;[^:]*)?:data:image/([^;]+);base64,(.+)$", re.IGNORECASE
)
_PHOTO_B64 = re.compile(r"^PHOTO(?:;[^:]*)?:(.+)$", re.IGNORECASE)


def _parse_param_tokens(param_str: Optional[str]) -> list[tuple[str, str]]:
    """解析属性参数；引号内的分号不拆分（如 TYPE=\"HOME;FAX\"）。"""
    if not param_str:
        return []
    tokens: list[str] = []
    current: list[str] = []
    in_quote = False
    for ch in param_str:
        if ch == '"':
            in_quote = not in_quote
            current.append(ch)
        elif ch == ";" and not in_quote:
            token = "".join(current).strip()
            if token:
                tokens.append(token)
            current = []
        else:
            current.append(ch)
    token = "".join(current).strip()
    if token:
        tokens.append(token)

    pairs: list[tuple[str, str]] = []
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        pairs.append((key.upper(), value.strip().strip('"')))
    return pairs


def _parse_params(param_str: Optional[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for key, value in _parse_param_tokens(param_str):
        params[key] = value
    return params


def _parse_property_line(line: str) -> tuple[str, list[tuple[str, str]], str]:
    key_part, value = line.split(":", 1)
    match = _PARAM_RE.match(key_part)
    if not match:
        return key_part.upper(), [], value
    name = match.group(1).upper()
    param_tokens = _parse_param_tokens(match.group(2))
    return name, param_tokens, value


def _expand_type_values(raw: str) -> tuple[list[str], bool]:
    types: list[str] = []
    extra_pref = False
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        upper = part.upper()
        if upper == "PREF" or part == "1":
            extra_pref = True
            continue
        if upper.startswith("PREF="):
            if part.split("=", 1)[1].strip() in ("1", "true", "TRUE"):
                extra_pref = True
            continue
        if ";" in part:
            types.extend(t for t in part.split(";") if t)
        else:
            types.append(part)
    return types, extra_pref


def _parse_tel(param_tokens: list[tuple[str, str]], value: str) -> Phone:
    types: list[str] = []
    pref = False
    for key, val in param_tokens:
        if key == "TYPE":
            expanded, type_pref = _expand_type_values(val)
            types.extend(expanded)
            pref = pref or type_pref
        elif key == "PREF" and val.strip() in ("1", "true", "TRUE"):
            pref = True
    if not types:
        types = ["CELL"]
    return Phone(number=value.strip(), types=types, pref=pref)


def _parse_email(param_tokens: list[tuple[str, str]], value: str) -> Email:
    types: list[str] = []
    for key, val in param_tokens:
        if key == "TYPE":
            expanded, _ = _expand_type_values(val)
            types.extend(expanded)
    if not types:
        types = ["HOME"]
    return Email(address=value.strip(), types=types)


def _parse_photo(line: str) -> Optional[bytes]:
    data_uri = _PHOTO_DATA_URI.match(line)
    if data_uri:
        return base64.b64decode(data_uri.group(2))
    plain = _PHOTO_B64.match(line)
    if plain and not plain.group(1).lower().startswith("data:"):
        raw = plain.group(1).replace("\n", "").replace(" ", "")
        try:
            return base64.b64decode(raw)
        except Exception:
            return None
    return None


def _parse_vcard_block(lines: list[str], source: Optional[str]) -> Contact:
    contact = Contact(fn="", source=source)
    pending_phones: list[Phone] = []
    pending_emails: list[Email] = []
    phonetic_family = ""
    phonetic_given = ""

    for line in lines:
        if line.upper() in ("BEGIN:VCARD", "END:VCARD"):
            continue
        name, param_tokens, value = _parse_property_line(line)

        if name == "FN":
            contact.fn = value.strip()
        elif name == "N":
            parts = value.split(";")
            while len(parts) < 5:
                parts.append("")
            if parts[0].strip():
                contact.n_family = parts[0].strip()
            if parts[1].strip():
                contact.n_given = parts[1].strip()
            elif parts[0].strip() and not parts[1].strip():
                contact.n_given = parts[0].strip()
                contact.n_family = ""
        elif name == "TEL":
            pending_phones.append(_parse_tel(param_tokens, value))
        elif name == "EMAIL":
            pending_emails.append(_parse_email(param_tokens, value))
        elif name == "ORG":
            contact.org = value.strip() or None
        elif name == "TITLE":
            contact.title = value.strip()
        elif name == "NOTE":
            contact.note = value.strip() or None
        elif name == "URL":
            contact.url = value.strip() or None
        elif name == "UID":
            contact.id = value.strip()
        elif name == "PHOTO":
            contact.photo = _parse_photo(line)
        elif name in ("SORT-STRING", "X-SORT-STRING"):
            contact.sort_string = value.strip()
        elif name == "X-PHONETIC-LAST-NAME":
            phonetic_family = value.strip()
        elif name == "X-PHONETIC-FIRST-NAME":
            phonetic_given = value.strip()

    if not contact.sort_string and (phonetic_family or phonetic_given):
        contact.sort_string = phonetic_family + phonetic_given

    if not contact.fn and (contact.n_family or contact.n_given):
        contact.fn = (contact.n_family or "") + (contact.n_given or "")
    if not contact.n_given and contact.fn and not contact.n_family:
        contact.n_given = contact.fn

    for idx, phone in enumerate(pending_phones):
        phone.sort_order = idx
    for idx, email in enumerate(pending_emails):
        email.sort_order = idx

    contact.phones = pending_phones
    contact.emails = pending_emails
    return contact


def parse_vcf_text(text: str, source: Optional[str] = None) -> list[Contact]:
    logical = unfold_lines(text)
    contacts: list[Contact] = []
    block: list[str] = []
    in_card = False

    for line in logical:
        upper = line.upper()
        if upper == "BEGIN:VCARD":
            in_card = True
            block = [line]
            continue
        if in_card:
            block.append(line)
            if upper == "END:VCARD":
                contact = _parse_vcard_block(block, source)
                if contact.fn or contact.phones:
                    contacts.append(contact)
                in_card = False
                block = []
    return contacts


def parse_vcf_file(path: Path | str) -> list[Contact]:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_vcf_text(text, source=path.name)
