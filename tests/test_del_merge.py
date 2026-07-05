import unittest
from pathlib import Path
from unittest.mock import patch

from contacttools.models.contact import Contact, Email, Phone
from contacttools.ops.delete_contact import build_delete_plan, delete_contacts
from contacttools.ops.merge import merge_contacts
from contacttools.ops.merge_interactive import merge_contacts_interactive
from contacttools.store.database import DEFAULT_DB_PATH, Database


class DeleteContactTest(unittest.TestCase):
    def test_delete_cascades_phones(self):
        db_path = DEFAULT_DB_PATH.parent / "test_del_contact.sqlite"
        db_path.unlink(missing_ok=True)
        try:
            with Database(db_path) as db:
                db.init_schema()
                c = Contact(fn="测试", phones=[Phone(number="13800000001")])
                db.save_contact(c)
                cid = c.id
                plan = build_delete_plan(db, [cid])
                self.assertEqual(plan.contact_count, 1)
                self.assertEqual(plan.phone_count, 1)

                with patch("builtins.input", return_value="y"):
                    result = delete_contacts(db, [cid], require_confirm=True)
                self.assertEqual(result["deleted"], 1)
                self.assertIsNone(db.get_contact(cid))
                row = db.conn.execute(
                    "SELECT COUNT(*) FROM phones WHERE contact_id = ?", (cid,)
                ).fetchone()[0]
                self.assertEqual(row, 0)
        finally:
            db_path.unlink(missing_ok=True)


class MergeContactScriptTest(unittest.TestCase):
    def test_simple_merge_by_id(self):
        db_path = DEFAULT_DB_PATH.parent / "test_merge_script.sqlite"
        db_path.unlink(missing_ok=True)
        try:
            with Database(db_path) as db:
                db.init_schema()
                a = Contact(fn="张三", phones=[Phone(number="111")])
                b = Contact(fn="张三", phones=[Phone(number="222")])
                db.save_contact(a)
                db.save_contact(b)
                with patch("builtins.input", return_value="y"):
                    kept = merge_contacts(
                        db, a.id, [b.id], require_confirm=True
                    )
                self.assertEqual(len(kept.phones), 2)
                self.assertEqual(db.count_contacts(), 1)
        finally:
            db_path.unlink(missing_ok=True)

    def test_simple_merge_emails(self):
        db_path = DEFAULT_DB_PATH.parent / "test_merge_email.sqlite"
        db_path.unlink(missing_ok=True)
        try:
            with Database(db_path) as db:
                db.init_schema()
                a = Contact(
                    fn="张三",
                    phones=[Phone(number="111")],
                    emails=[Email(address="a@x.com")],
                )
                b = Contact(
                    fn="张三",
                    phones=[Phone(number="222")],
                    emails=[Email(address="b@x.com")],
                )
                db.save_contact(a)
                db.save_contact(b)
                with patch("builtins.input", return_value="y"):
                    kept = merge_contacts(
                        db, a.id, [b.id], require_confirm=True
                    )
                self.assertEqual(len(kept.phones), 2)
                self.assertEqual(len(kept.emails), 2)
        finally:
            db_path.unlink(missing_ok=True)

    def test_interactive_merge_choices(self):
        db_path = DEFAULT_DB_PATH.parent / "test_merge_interactive.sqlite"
        db_path.unlink(missing_ok=True)
        inputs = iter(["d", "", "y"])
        try:
            with Database(db_path) as db:
                db.init_schema()
                a = Contact(fn="张三", org="单位A", phones=[Phone(number="111")])
                b = Contact(fn="张三", org="单位B", phones=[Phone(number="222")])
                db.save_contact(a)
                db.save_contact(b)
                with patch("builtins.input", lambda _: next(inputs)):
                    kept = merge_contacts_interactive(
                        db, a.id, [b.id], require_confirm=True
                    )
                self.assertEqual(kept.org, "单位B")
                self.assertEqual(len(kept.phones), 2)
                self.assertEqual(db.count_contacts(), 1)
        finally:
            db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
