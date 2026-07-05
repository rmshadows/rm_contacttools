from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from contacttools.models.contact import Contact, Email, Phone
from contacttools.normalize.pinyin import fn_pinyin_for_contact, name_to_pinyin

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_VIEWS_PATH = Path(__file__).with_name("views.sql")
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "contacts.sqlite"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _types_to_str(types: list[str]) -> str:
    return ";".join(types) if types else "CELL"


def _types_from_str(raw: str) -> list[str]:
    if not raw:
        return ["CELL"]
    return [t for t in raw.split(";") if t]


class Database:
    def __init__(self, path: Path | str = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def init_schema(self) -> None:
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn.executescript(sql)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        cols = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(contacts)").fetchall()
        }
        if "n_family" not in cols:
            self.conn.execute("ALTER TABLE contacts ADD COLUMN n_family TEXT")
        if "fn_pinyin" not in cols:
            self.conn.execute("ALTER TABLE contacts ADD COLUMN fn_pinyin TEXT")
            self.backfill_fn_pinyin(commit=False)
        self._migrate_views()

    def _migrate_views(self) -> None:
        sql = _VIEWS_PATH.read_text(encoding="utf-8")
        self.conn.executescript(sql)

    def backfill_fn_pinyin(self, *, commit: bool = True) -> int:
        """按 fn 重新生成 fn_pinyin（DBeaver 改姓名后调用）。"""
        rows = self.conn.execute("SELECT id, fn, fn_pinyin FROM contacts").fetchall()
        changed = 0
        for row in rows:
            key = name_to_pinyin(row["fn"]) or None
            if row["fn_pinyin"] != key:
                self.conn.execute(
                    "UPDATE contacts SET fn_pinyin = ? WHERE id = ?",
                    (key, row["id"]),
                )
                changed += 1
        if commit:
            self.conn.commit()
        return changed

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def count_contacts(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM contacts").fetchone()
        return int(row[0])

    def clear_all(self) -> None:
        self.conn.execute("DELETE FROM emails")
        self.conn.execute("DELETE FROM phones")
        self.conn.execute("DELETE FROM contacts")
        self.conn.commit()

    def clear_history(self) -> None:
        self.conn.execute("DELETE FROM merge_history")
        self.conn.execute("DELETE FROM import_batches")
        self.conn.commit()

    def save_contact(self, contact: Contact) -> None:
        now = _utc_now()
        if contact.imported_at is None:
            contact.imported_at = datetime.fromisoformat(now)
        contact.touch()
        fn_pinyin = fn_pinyin_for_contact(contact) or None

        self.conn.execute(
            """
            INSERT INTO contacts (
                id, fn, fn_pinyin, n_family, n_given, org, title, note, url, photo,
                source, imported_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                fn=excluded.fn,
                fn_pinyin=excluded.fn_pinyin,
                n_family=excluded.n_family,
                n_given=excluded.n_given,
                org=excluded.org,
                title=excluded.title,
                note=excluded.note,
                url=excluded.url,
                photo=excluded.photo,
                source=excluded.source,
                updated_at=excluded.updated_at
            """,
            (
                contact.id,
                contact.fn,
                fn_pinyin,
                contact.n_family or None,
                contact.n_given,
                contact.org,
                contact.title,
                contact.note,
                contact.url,
                contact.photo,
                contact.source,
                contact.imported_at.isoformat(),
                contact.updated_at.isoformat() if contact.updated_at else now,
            ),
        )
        self.conn.execute("DELETE FROM phones WHERE contact_id = ?", (contact.id,))
        self.conn.execute("DELETE FROM emails WHERE contact_id = ?", (contact.id,))

        for phone in contact.phones:
            self.conn.execute(
                """
                INSERT INTO phones (contact_id, number, types, pref, sort_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    contact.id,
                    phone.number,
                    _types_to_str(phone.types),
                    1 if phone.pref else 0,
                    phone.sort_order,
                ),
            )

        for email in contact.emails:
            self.conn.execute(
                """
                INSERT INTO emails (contact_id, address, types, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (
                    contact.id,
                    email.address,
                    _types_to_str(email.types),
                    email.sort_order,
                ),
            )
        self.conn.commit()

    def delete_contact(self, contact_id: str) -> None:
        self.conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        self.conn.commit()

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        row = self.conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_contact(row)

    def list_contacts(self) -> list[Contact]:
        rows = self.conn.execute(
            """
            SELECT * FROM contacts
            ORDER BY fn_pinyin COLLATE NOCASE, fn COLLATE NOCASE
            """
        ).fetchall()
        return [self._row_to_contact(row) for row in rows]

    def find_contact_ids_by_phone(self, number: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT contact_id FROM phones WHERE number = ?", (number,)
        ).fetchall()
        return [row[0] for row in rows]

    def record_import(self, filename: str, contact_count: int, mode: str) -> None:
        self.conn.execute(
            """
            INSERT INTO import_batches (filename, imported_at, contact_count, mode)
            VALUES (?, ?, ?, ?)
            """,
            (filename, _utc_now(), contact_count, mode),
        )
        self.conn.commit()

    def _row_to_contact(self, row: sqlite3.Row) -> Contact:
        contact_id = row["id"]
        phone_rows = self.conn.execute(
            """
            SELECT number, types, pref, sort_order
            FROM phones WHERE contact_id = ?
            ORDER BY sort_order, id
            """,
            (contact_id,),
        ).fetchall()
        email_rows = self.conn.execute(
            """
            SELECT address, types, sort_order
            FROM emails WHERE contact_id = ?
            ORDER BY sort_order, id
            """,
            (contact_id,),
        ).fetchall()

        phones = [
            Phone(
                number=pr["number"],
                types=_types_from_str(pr["types"]),
                pref=bool(pr["pref"]),
                sort_order=pr["sort_order"],
            )
            for pr in phone_rows
        ]
        emails = [
            Email(
                address=er["address"],
                types=_types_from_str(er["types"]),
                sort_order=er["sort_order"],
            )
            for er in email_rows
        ]

        imported_at = (
            datetime.fromisoformat(row["imported_at"]) if row["imported_at"] else None
        )
        updated_at = (
            datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        )

        return Contact(
            id=contact_id,
            fn=row["fn"],
            n_family=row["n_family"] or "",
            n_given=row["n_given"],
            org=row["org"],
            title=row["title"],
            note=row["note"],
            url=row["url"],
            photo=row["photo"],
            source=row["source"],
            imported_at=imported_at,
            updated_at=updated_at,
            phones=phones,
            emails=emails,
        )

    def save_contacts(self, contacts: Iterable[Contact]) -> int:
        count = 0
        for contact in contacts:
            self.save_contact(contact)
            count += 1
        return count

    def duplicate_phone_report(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT number, contact_count, contact_ids
            FROM v_duplicate_phones
            ORDER BY contact_count DESC, number
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def merge_history_snapshot(self, kept_id: str, merged: Contact) -> None:
        payload = json.dumps(
            {
                "id": merged.id,
                "fn": merged.fn,
                "phones": [
                    {"number": p.number, "types": p.types, "pref": p.pref}
                    for p in merged.phones
                ],
            },
            ensure_ascii=False,
        )
        self.conn.execute(
            """
            INSERT INTO merge_history (kept_id, merged_id, merged_snapshot, merged_at)
            VALUES (?, ?, ?, ?)
            """,
            (kept_id, merged.id, payload, _utc_now()),
        )
        self.conn.commit()
