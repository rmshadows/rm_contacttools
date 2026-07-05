import unittest
from pathlib import Path

from contacttools.models.contact import Contact, Phone
from contacttools.ops.diff import contacts_semantically_equal
from contacttools.ops.import_vcf import import_vcf
from contacttools.ops.plan import build_import_plan
from contacttools.store.database import Database

ROOT = Path(__file__).resolve().parents[1]


class AppendImportTest(unittest.TestCase):
    def test_semantic_equal_ignores_id(self):
        a = Contact(id="a", fn="张三", phones=[Phone(number="13800000001")])
        b = Contact(id="b", fn="张三", phones=[Phone(number="13800000001")])
        self.assertTrue(contacts_semantically_equal(a, b))

    def test_append_skips_identical(self):
        db_path = ROOT / "data" / "test_append_skip.sqlite"
        db_path.unlink(missing_ok=True)
        with Database(db_path) as db:
            db.init_schema()
            db.save_contact(
                Contact(fn="李四", phones=[Phone(number="13900000001")])
            )
            plan = build_import_plan(
                db,
                [Contact(fn="李四", phones=[Phone(number="13900000001")])],
                "append",
            )
            self.assertEqual(plan.skip_count, 1)
            self.assertEqual(plan.insert_count, 0)
        db_path.unlink(missing_ok=True)

    def test_append_inserts_when_extra_phone(self):
        db_path = ROOT / "data" / "test_append_phone.sqlite"
        db_path.unlink(missing_ok=True)
        with Database(db_path) as db:
            db.init_schema()
            db.save_contact(
                Contact(
                    fn="张三",
                    phones=[
                        Phone(number="13800000001"),
                        Phone(number="13800000002"),
                    ],
                )
            )
            incoming = Contact(
                fn="张三",
                phones=[
                    Phone(number="13800000001"),
                    Phone(number="13800000002"),
                    Phone(number="13800000003"),
                ],
            )
            plan = build_import_plan(db, [incoming], "append")
            self.assertEqual(plan.insert_count, 1)
            self.assertEqual(plan.skip_count, 0)

            tmp_vcf = ROOT / "data" / "test_append_in.vcf"
            tmp_vcf.write_text(
                "BEGIN:VCARD\nVERSION:4.0\nFN:张三\n"
                "TEL;TYPE=CELL:13800000001\n"
                "TEL;TYPE=CELL:13800000002\n"
                "TEL;TYPE=CELL:13800000003\n"
                "END:VCARD\n",
                encoding="utf-8",
            )
            try:
                import_vcf(tmp_vcf, db, mode="append", require_confirm=False)
                self.assertEqual(db.count_contacts(), 2)
            finally:
                tmp_vcf.unlink(missing_ok=True)
        db_path.unlink(missing_ok=True)

    def test_append_inserts_when_name_diff(self):
        db_path = ROOT / "data" / "test_append_name.sqlite"
        db_path.unlink(missing_ok=True)
        with Database(db_path) as db:
            db.init_schema()
            db.save_contact(
                Contact(fn="错名", phones=[Phone(number="13800000001")])
            )
            plan = build_import_plan(
                db,
                [Contact(fn="正确名", phones=[Phone(number="13800000001")])],
                "append",
            )
            self.assertEqual(plan.insert_count, 1)
        db_path.unlink(missing_ok=True)

    def test_append_note_diff_not_equal(self):
        a = Contact(fn="王五", note="旧", phones=[Phone(number="13700000001")])
        b = Contact(fn="王五", note="新", phones=[Phone(number="13700000001")])
        self.assertFalse(contacts_semantically_equal(a, b))


if __name__ == "__main__":
    unittest.main()
