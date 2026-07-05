from __future__ import annotations

from pathlib import Path

from contacttools.store.database import Database
from contacttools.vcf.writer import write_vcf_file


def export_vcf(db: Database, output_path: Path | str) -> dict:
    contacts = db.list_contacts()
    path = Path(output_path)
    write_vcf_file(contacts, path)
    return {
        "file": str(path),
        "count": len(contacts),
    }
