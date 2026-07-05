from __future__ import annotations

from dataclasses import dataclass, field

from contacttools.store.database import Database


@dataclass
class DeletePlan:
    contact_ids: list[str]
    lines: list[str] = field(default_factory=list)
    contact_count: int = 0
    phone_count: int = 0
    email_count: int = 0
    missing_ids: list[str] = field(default_factory=list)
    valid_ids: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        header = [
            "【删除预览 — 尚未写入】",
            f"将删除联系人: {self.contact_count} 条",
            f"连带删除 phones: {self.phone_count} 条, emails: {self.email_count} 条",
            "（删 contacts 行时外键 ON DELETE CASCADE，不会留下孤儿记录）",
            "",
        ]
        if self.missing_ids:
            header.append("【以下 id 在库中不存在，将忽略】")
            for cid in self.missing_ids:
                header.append(f"  ? {cid}")
            header.append("")
        if not self.lines:
            header.append("  (无有效 id)")
            return "\n".join(header)
        header.extend(self.lines)
        return "\n".join(header)


def _child_counts(db: Database, contact_id: str) -> tuple[int, int]:
    phones = db.conn.execute(
        "SELECT COUNT(*) FROM phones WHERE contact_id = ?", (contact_id,)
    ).fetchone()[0]
    emails = db.conn.execute(
        "SELECT COUNT(*) FROM emails WHERE contact_id = ?", (contact_id,)
    ).fetchone()[0]
    return int(phones), int(emails)


def _phones_label(db: Database, contact_id: str) -> str:
    rows = db.conn.execute(
        "SELECT number FROM phones WHERE contact_id = ? ORDER BY sort_order, id",
        (contact_id,),
    ).fetchall()
    nums = [row[0] for row in rows if row[0]]
    return ", ".join(nums) if nums else "(无号码)"


def build_delete_plan(db: Database, contact_ids: list[str]) -> DeletePlan:
    plan = DeletePlan(contact_ids=list(contact_ids))
    seen: set[str] = set()

    for raw in contact_ids:
        cid = raw.strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)

        row = db.conn.execute(
            "SELECT fn, org FROM contacts WHERE id = ?", (cid,)
        ).fetchone()
        if row is None:
            plan.missing_ids.append(cid)
            continue

        phone_n, email_n = _child_counts(db, cid)
        plan.contact_count += 1
        plan.phone_count += phone_n
        plan.email_count += email_n
        plan.valid_ids.append(cid)
        org = f"  ORG={row['org']}" if row["org"] else ""
        plan.lines.append(
            f"  - 删除  {row['fn']}{org}  id={cid[:8]}…  号码: {_phones_label(db, cid)}"
        )

    return plan


def delete_contacts(
    db: Database,
    contact_ids: list[str],
    *,
    require_confirm: bool = True,
) -> dict:
    from contacttools.ops.confirm import confirm_or_cancel

    plan = build_delete_plan(db, contact_ids)
    if plan.contact_count == 0:
        return {
            "deleted": 0,
            "phones_removed": 0,
            "emails_removed": 0,
            "missing_ids": plan.missing_ids,
            "cancelled": False,
            "empty": True,
        }

    if require_confirm:
        if not confirm_or_cancel(plan.as_text(), "删除联系人"):
            return {
                "deleted": 0,
                "phones_removed": 0,
                "emails_removed": 0,
                "missing_ids": plan.missing_ids,
                "cancelled": True,
                "empty": False,
            }

    deleted = 0
    for cid in plan.valid_ids:
        db.delete_contact(cid)
        deleted += 1

    return {
        "deleted": deleted,
        "phones_removed": plan.phone_count,
        "emails_removed": plan.email_count,
        "missing_ids": plan.missing_ids,
        "cancelled": False,
        "empty": False,
        "total_in_db": db.count_contacts(),
    }
