import tempfile
import unittest
from pathlib import Path

from contacttools.ops.add_contact import (
    add_contacts,
    build_contact,
    parse_contacts_file,
    phone_conflicts,
)
from contacttools.store.database import DEFAULT_DB_PATH, Database


class AddContactTest(unittest.TestCase):
    def test_build_contact_multi_phone(self):
        contact = build_contact(
            "张三",
            ["13800138000", "13900139000"],
            org="测试公司",
            note="备注甲",
        )
        self.assertIsNotNone(contact)
        assert contact is not None
        self.assertEqual(contact.org, "测试公司")
        self.assertEqual(contact.note, "备注甲")
        self.assertEqual(len(contact.phones), 2)
        self.assertEqual(contact.phones[0].number, "13800138000")
        self.assertTrue(contact.phones[0].pref)
        self.assertFalse(contact.phones[1].pref)

    def test_build_contact_invalid_phone(self):
        self.assertIsNone(build_contact("李四", []))

    def test_parse_merge_same_name(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write("张三\t13800138000\t公司A\t备注1\n")
            f.write("张三\t13900139000\t公司A\t备注1\n")
            f.write("李四 10086\n")
            path = Path(f.name)
        try:
            contacts, errors = parse_contacts_file(path)
            self.assertEqual(len(contacts), 2)
            self.assertEqual(len(errors), 0)
            zhang = next(c for c in contacts if c.fn == "张三")
            self.assertEqual(len(zhang.phones), 2)
            self.assertEqual(zhang.org, "公司A")
            self.assertEqual(zhang.note, "备注1")
            li = next(c for c in contacts if c.fn == "李四")
            self.assertEqual(li.phones[0].number, "10086")
            self.assertIsNone(li.org)
        finally:
            path.unlink()

    def test_parse_space_with_note(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write("王五 138000 单位A 这是备注内容\n")
            path = Path(f.name)
        try:
            contacts, errors = parse_contacts_file(path)
            self.assertEqual(len(contacts), 1)
            self.assertEqual(contacts[0].org, "单位A")
            self.assertEqual(contacts[0].note, "这是备注内容")
        finally:
            path.unlink()

    def test_parse_bad_line(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write("只有姓名\n")
            path = Path(f.name)
        try:
            contacts, errors = parse_contacts_file(path)
            self.assertEqual(len(contacts), 0)
            self.assertEqual(len(errors), 1)
        finally:
            path.unlink()

    def test_add_and_skip_identical(self):
        db_path = DEFAULT_DB_PATH.parent / "test_add_contact.sqlite"
        db_path.unlink(missing_ok=True)
        try:
            with Database(db_path) as db:
                db.init_schema()
                c1 = build_contact("王五", ["10086"], org="A")
                assert c1 is not None
                r1 = add_contacts(db, [c1])
                self.assertEqual(r1["saved"], 1)

                c2 = build_contact("王五", ["10086"], org="A")
                assert c2 is not None
                r2 = add_contacts(db, [c2])
                self.assertEqual(r2["saved"], 0)
                self.assertEqual(r2["skipped"], 1)
        finally:
            db_path.unlink(missing_ok=True)

    def test_phone_conflicts(self):
        db_path = DEFAULT_DB_PATH.parent / "test_add_conflict.sqlite"
        db_path.unlink(missing_ok=True)
        try:
            with Database(db_path) as db:
                db.init_schema()
                existing = build_contact("旧人", ["10010"])
                assert existing is not None
                db.save_contact(existing)

                newcomer = build_contact("新人", ["10010"])
                assert newcomer is not None
                conflicts = phone_conflicts(db, newcomer)
                self.assertEqual(len(conflicts), 1)
        finally:
            db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
