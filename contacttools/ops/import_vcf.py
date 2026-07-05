from __future__ import annotations

from pathlib import Path
from typing import Literal

from contacttools.models.contact import Contact, new_id
from contacttools.normalize.name import NameMode, normalize_name
from contacttools.normalize.pinyin import apply_fn_pinyin
from contacttools.normalize.phone import normalize_contact_phones
from contacttools.ops.contact_merge import merge_contact_fields
from contacttools.ops.diff import find_identical_contact, summarize_new
from contacttools.ops.confirm import confirm_plan_with_report
from contacttools.ops.plan import build_import_plan
from contacttools.store.database import Database
from contacttools.vcf.parser import parse_vcf_file

ImportMode = Literal["replace", "append", "upsert"]
IMPORT_PREVIEW_FILENAME = "import_preview.txt"


def _prepare_contacts(vcf_path: Path, name_mode: NameMode = "fullname") -> list[Contact]:
    contacts = parse_vcf_file(vcf_path)
    for contact in contacts:
        normalize_contact_phones(contact)
        normalize_name(contact, name_mode)
        apply_fn_pinyin(contact)
        if not contact.id:
            contact.id = new_id()
    return contacts


def import_vcf(
    vcf_path: Path | str,
    db: Database,
    mode: ImportMode = "replace",
    *,
    name_mode: NameMode = "fullname",
    require_confirm: bool = True,
) -> dict:
    path = Path(vcf_path)
    contacts = _prepare_contacts(path, name_mode)

    plan = build_import_plan(db, contacts, mode)
    if require_confirm:
        preview_path = db.path.parent / IMPORT_PREVIEW_FILENAME
        if not confirm_plan_with_report(
            plan.as_text(),
            plan.terminal_summary(),
            preview_path,
            f"导入 VCF ({mode})",
        ):
            return {
                "file": str(path),
                "parsed": len(contacts),
                "saved": 0,
                "skipped": 0,
                "mode": mode,
                "total_in_db": db.count_contacts(),
                "cancelled": True,
            }

    if mode == "replace":
        db.clear_all()
        saved = 0
        skipped = 0
        for contact in contacts:
            db.save_contact(contact)
            saved += 1
    elif mode == "append":
        saved = 0
        skipped = 0
        for contact in contacts:
            if find_identical_contact(db, contact):
                skipped += 1
                continue
            contact.id = new_id()
            db.save_contact(contact)
            saved += 1
    else:
        saved = 0
        skipped = 0
        for contact in contacts:
            numbers = [p.number for p in contact.phones if p.number]
            existing_ids: set[str] = set()
            for n in numbers:
                existing_ids.update(db.find_contact_ids_by_phone(n))
            if existing_ids:
                contact.id = sorted(existing_ids)[0]
                existing = db.get_contact(contact.id)
                if existing:
                    contact = merge_contact_fields(existing, contact)
                db.save_contact(contact)
                saved += 1
            else:
                contact.id = new_id()
                db.save_contact(contact)
                saved += 1

    db.record_import(path.name, len(contacts), mode)
    return {
        "file": str(path),
        "parsed": len(contacts),
        "saved": saved,
        "skipped": skipped,
        "mode": mode,
        "total_in_db": db.count_contacts(),
        "cancelled": False,
    }


def preview_import_vcf(
    vcf_path: Path | str,
    db: Database,
    mode: ImportMode = "replace",
    *,
    name_mode: NameMode = "fullname",
) -> str:
    """仅预览导入变更，不写库。"""
    contacts = _prepare_contacts(Path(vcf_path), name_mode)
    return build_import_plan(db, contacts, mode).as_text()
