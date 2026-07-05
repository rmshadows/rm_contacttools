import unittest
from pathlib import Path

from contacttools.models.contact import Contact, Phone
from contacttools.normalize.name import (
    classify_same_name_group,
    format_warnings,
    normalize_name,
    normalize_split_name,
    normalize_to_fullname,
)
from contacttools.ops.name_review import find_same_name_groups
from contacttools.store.database import Database
from contacttools.vcf.parser import parse_vcf_text

ROOT = Path(__file__).resolve().parents[1]

_VCARD_SAMPLE = "\n".join(
    [
        "BEGIN:VCARD",
        "FN:小明 张",
        "N:张;小明;;;",
        "TEL;TYPE=CELL:13800000008",
        "END:VCARD",
    ]
)


class NameNormalizeTest(unittest.TestCase):
    def test_fullname_mode(self):
        c = Contact(fn="小明 张", n_family="张", n_given="小明")
        normalize_to_fullname(c)
        self.assertEqual(c.fn, "小明 张")
        self.assertEqual(c.n_family, "")
        self.assertEqual(c.n_given, "小明 张")

    def test_split_mode(self):
        c = Contact(fn="小明 张", n_family="张", n_given="小明")
        normalize_split_name(c)
        self.assertEqual(c.fn, "小明 张")
        self.assertEqual(c.n_family, "张")
        self.assertEqual(c.n_given, "小明")
        self.assertEqual(format_warnings(c, name_mode="split"), [])

    def test_format_ok_after_fullname_normalize(self):
        c = Contact(fn="张三", n_family="张", n_given="三")
        normalize_to_fullname(c)
        self.assertEqual(c.fn, "张三")
        self.assertEqual(c.n_given, "张三")
        self.assertEqual(c.n_family, "")

    def test_merge_split_import_fullname(self):
        c = Contact(fn="", n_family="张", n_given="三")
        normalize_to_fullname(c)
        self.assertEqual(c.fn, "张三")

    def test_format_mismatch_fullname_mode(self):
        c = Contact(fn="张三", n_family="李", n_given="四")
        self.assertTrue(format_warnings(c, name_mode="fullname"))

    def test_vcf_import_split(self):
        contacts = parse_vcf_text(_VCARD_SAMPLE)
        normalize_name(contacts[0], "split")
        self.assertEqual(contacts[0].fn, "小明 张")
        self.assertEqual(contacts[0].n_family, "张")
        self.assertEqual(contacts[0].n_given, "小明")

    def test_vcf_import_fullname(self):
        contacts = parse_vcf_text(_VCARD_SAMPLE)
        normalize_name(contacts[0], "fullname")
        self.assertEqual(contacts[0].fn, "小明 张")
        self.assertEqual(contacts[0].n_family, "")
        self.assertEqual(contacts[0].n_given, "小明 张")

    def test_ambiguous_same_name(self):
        a = Contact(fn="王伟", id="a", phones=[Phone(number="13800000001")])
        b = Contact(fn="王伟", id="b", phones=[Phone(number="13900000002")])
        risk, _ = classify_same_name_group([a, b])
        self.assertEqual(risk, "ambiguous")

    def test_same_name_group_in_db(self):
        db_path = ROOT / "data" / "test_name.sqlite"
        db_path.unlink(missing_ok=True)
        with Database(db_path) as db:
            db.init_schema()
            c1 = Contact(fn="李四", n_given="李四", phones=[Phone(number="111")])
            c2 = Contact(fn="李四", n_family="李", n_given="四", phones=[Phone(number="222")])
            db.save_contact(c1)
            db.save_contact(c2)
            self.assertEqual(len(find_same_name_groups(db)), 1)
        db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
