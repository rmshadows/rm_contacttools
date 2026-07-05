from __future__ import annotations

import copy

from contacttools.models.contact import Contact, Email, Phone
from contacttools.normalize.pinyin import apply_fn_pinyin
from contacttools.ops.confirm import ask_confirm
from contacttools.ops.diff import copy_contact, diff_contact_fields
from contacttools.store.database import Database

_TEXT_FIELDS: tuple[tuple[str, str], ...] = (
    ("fn", "显示名 FN"),
    ("n_family", "姓 n_family"),
    ("n_given", "名 n_given"),
    ("org", "单位 ORG"),
    ("title", "职务 TITLE"),
    ("note", "备注 NOTE"),
    ("url", "网址 URL"),
)


def _display(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _read_line(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        raise RuntimeError("用户取消操作，数据库未修改")


def _prompt_text_field(
    label: str, keep_val: str | None, drop_val: str | None
) -> str | None:
    k = _display(keep_val)
    d = _display(drop_val)

    if k == d:
        return keep_val if keep_val is not None else drop_val

    if k and not d:
        print(f"  {label}: 仅保留侧有值 → {k!r}")
        return keep_val

    if d and not k:
        while True:
            ans = _read_line(
                f"  {label}: keep 空，drop={d!r}  [d=采用 drop / k=留空] (默认 d): "
            ).lower()
            if ans in ("", "d", "drop", "采用"):
                return drop_val
            if ans in ("k", "keep", "空", "留空"):
                return keep_val
            print("    请输入 d 或 k。")

    while True:
        print(f"  {label} — 两侧不同:")
        print(f"    [k] keep: {k!r}")
        print(f"    [d] drop: {d!r}")
        print("    [e] 手动输入")
        ans = _read_line("    选择 [k/d/e] (默认 k): ").lower()
        if ans in ("", "k", "keep"):
            return keep_val
        if ans in ("d", "drop"):
            return drop_val
        if ans in ("e", "edit", "手动"):
            typed = _read_line("    输入新值（留空表示清空）: ")
            return typed or None
        print("    请输入 k、d 或 e。")


def _prompt_photo(keep: Contact, drop: Contact) -> bytes | None:
    has_k = bool(keep.photo)
    has_d = bool(drop.photo)
    if has_k and not has_d:
        print("  头像: 仅 keep 有 → 保留")
        return keep.photo
    if has_d and not has_k:
        while True:
            ans = _read_line("  头像: 仅 drop 有 → [d=采用 / k=不要] (默认 d): ").lower()
            if ans in ("", "d"):
                return drop.photo
            if ans in ("k", "n", "不要"):
                return None
    if has_k and has_d:
        if keep.photo == drop.photo:
            return keep.photo
        while True:
            print("  头像 — 两侧都有:")
            ans = _read_line("    [k] keep / [d] drop / [n] 都不要 (默认 k): ").lower()
            if ans in ("", "k"):
                return keep.photo
            if ans in ("d",):
                return drop.photo
            if ans in ("n", "none", "不要"):
                return None
    return None


def _phone_items(keep: Contact, drop: Contact) -> list[tuple[Phone, str]]:
    items: list[tuple[Phone, str]] = []
    seen: set[str] = set()
    for phone in keep.phones:
        if phone.number and phone.number not in seen:
            items.append((copy.copy(phone), "keep"))
            seen.add(phone.number)
    for phone in drop.phones:
        if phone.number and phone.number not in seen:
            items.append((copy.copy(phone), "drop"))
            seen.add(phone.number)
    return items


def _prompt_phones(keep: Contact, drop: Contact) -> list[Phone]:
    items = _phone_items(keep, drop)
    if not items:
        print("  电话: (两侧均无)")
        return []

    print("  电话 — 默认全部保留；输入不要的序号（空格分隔），回车=全要:")
    for idx, (phone, src) in enumerate(items, 1):
        types = "/".join(phone.types) or "CELL"
        pref = " PREF" if phone.pref else ""
        print(f"    {idx}. [{src}] {phone.number} ({types}{pref})")

    while True:
        ans = _read_line("    排除序号: ")
        if not ans:
            excluded: set[int] = set()
            break
        try:
            excluded = {int(x) - 1 for x in ans.split()}
        except ValueError:
            print("    请输入数字序号，如: 2 3")
            continue
        if any(i < 0 or i >= len(items) for i in excluded):
            print("    序号超出范围。")
            continue
        break

    phones: list[Phone] = []
    for order, i in enumerate(i for i in range(len(items)) if i not in excluded):
        phone, _ = items[i]
        phone.sort_order = order
        phones.append(phone)
    return phones


def _email_items(keep: Contact, drop: Contact) -> list[tuple[Email, str]]:
    items: list[tuple[Email, str]] = []
    seen: set[str] = set()
    for email in keep.emails:
        key = email.address.lower()
        if email.address and key not in seen:
            items.append((copy.copy(email), "keep"))
            seen.add(key)
    for email in drop.emails:
        key = email.address.lower()
        if email.address and key not in seen:
            items.append((copy.copy(email), "drop"))
            seen.add(key)
    return items


def _prompt_emails(keep: Contact, drop: Contact) -> list[Email]:
    items = _email_items(keep, drop)
    if not items:
        return []

    print("  邮箱 — 默认全部保留；输入不要的序号，回车=全要:")
    for idx, (email, src) in enumerate(items, 1):
        print(f"    {idx}. [{src}] {email.address}")
    ans = _read_line("    排除序号: ")
    excluded: set[int] = set()
    if ans:
        try:
            excluded = {int(x) - 1 for x in ans.split()}
        except ValueError:
            excluded = set()

    emails: list[Email] = []
    for order, i in enumerate(i for i in range(len(items)) if i not in excluded):
        email, _ = items[i]
        email.sort_order = order
        emails.append(email)
    return emails


def _interactive_merge_pair(accumulated: Contact, drop: Contact) -> Contact:
    result = copy_contact(accumulated)
    print()
    print(f"--- 合并进: {drop.fn}  (id {drop.id[:8]}…) ---")

    for attr, label in _TEXT_FIELDS:
        keep_val = getattr(accumulated, attr)
        drop_val = getattr(drop, attr)
        if isinstance(keep_val, str):
            keep_val = keep_val or None
        if isinstance(drop_val, str):
            drop_val = drop_val or None
        chosen = _prompt_text_field(label, keep_val, drop_val)
        setattr(result, attr, chosen)

    result.photo = _prompt_photo(accumulated, drop)
    result.phones = _prompt_phones(accumulated, drop)
    result.emails = _prompt_emails(accumulated, drop)
    apply_fn_pinyin(result)
    return result


def _format_contact_summary(contact: Contact) -> str:
    phones = ", ".join(p.number for p in contact.phones if p.number) or "(无)"
    emails = ", ".join(e.address for e in contact.emails if e.address) or "(无)"
    lines = [
        f"  FN={contact.fn!r}",
        f"  姓={_display(contact.n_family)!r}  名={_display(contact.n_given)!r}",
        f"  ORG={contact.org!r}  NOTE={contact.note!r}",
        f"  电话: {phones}",
        f"  邮箱: {emails}",
        f"  头像: {'有' if contact.photo else '无'}",
    ]
    return "\n".join(lines)


def merge_contacts_interactive(
    db: Database,
    keep_id: str,
    drop_ids: list[str],
    *,
    require_confirm: bool = True,
) -> Contact:
    kept = db.get_contact(keep_id)
    if kept is None:
        raise ValueError(f"找不到联系人: {keep_id}")

    accumulated = copy_contact(kept)
    before = copy_contact(kept)
    to_delete: list[Contact] = []

    print()
    print("【交互合并】逐项选择保留侧 / drop 侧 / 手动输入")
    print(f"保留 id: {keep_id}")
    print()

    for drop_id in drop_ids:
        if drop_id == keep_id:
            continue
        other = db.get_contact(drop_id)
        if other is None:
            print(f"跳过不存在的 id: {drop_id}")
            continue
        accumulated = _interactive_merge_pair(accumulated, other)
        to_delete.append(other)

    if not to_delete:
        raise ValueError("没有可合并的 drop 记录")

    print()
    print("【合并结果预览】")
    print(_format_contact_summary(accumulated))
    changes = diff_contact_fields(before, accumulated)
    if changes:
        print("\n相对合并前变更:")
        print("\n".join(changes))
    print("\n将删除联系人:")
    for other in to_delete:
        print(f"  - {other.fn}  (id {other.id[:8]}…)")

    if require_confirm:
        print()
        if not ask_confirm("确认写入合并结果？"):
            raise RuntimeError("用户取消操作，数据库未修改")

    for other in to_delete:
        db.merge_history_snapshot(keep_id, other)
        db.delete_contact(other.id)

    accumulated.id = keep_id
    accumulated.touch()
    apply_fn_pinyin(accumulated)
    db.save_contact(accumulated)
    return accumulated
