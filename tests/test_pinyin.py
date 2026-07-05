import unittest

from contacttools.models.contact import Contact
from contacttools.normalize.pinyin import (
    apply_fn_pinyin,
    fn_pinyin_for_contact,
    name_to_pinyin,
    normalize_pinyin_key,
)
from contacttools.ops.import_vcf import import_vcf
from contacttools.store.database import DEFAULT_DB_PATH, Database
from contacttools.vcf.parser import parse_vcf_text


class PinyinTest(unittest.TestCase):
    def test_name_to_pinyin(self):
        self.assertEqual(name_to_pinyin("张三"), "zhangsan")
        self.assertEqual(name_to_pinyin("李四"), "lisi")
        self.assertLess(name_to_pinyin("李四"), name_to_pinyin("王五"))

    def test_normalize_pinyin_key(self):
        self.assertEqual(normalize_pinyin_key(" Zhang San "), "zhangsan")

    def test_sort_string_preferred(self):
        contact = Contact(fn="张三", sort_string="Zhang San")
        self.assertEqual(fn_pinyin_for_contact(contact), "zhangsan")

    def test_parse_vcf_sort_string(self):
        text = "\n".join(
            [
                "BEGIN:VCARD",
                "FN:测试",
                "SORT-STRING:ceshi",
                "TEL:10000",
                "END:VCARD",
            ]
        )
        contacts = parse_vcf_text(text)
        self.assertEqual(len(contacts), 1)
        apply_fn_pinyin(contacts[0])
        self.assertEqual(contacts[0].fn_pinyin, "ceshi")

    def test_import_writes_fn_pinyin(self):
        db_path = DEFAULT_DB_PATH.parent / "test_pinyin.sqlite"
        db_path.unlink(missing_ok=True)
        vcf = "\n".join(
            [
                "BEGIN:VCARD",
                "FN:王五",
                "TEL:10001",
                "END:VCARD",
                "BEGIN:VCARD",
                "FN:李四",
                "TEL:10002",
                "END:VCARD",
            ]
        )
        vcf_path = db_path.with_suffix(".vcf")
        vcf_path.write_text(vcf, encoding="utf-8")
        try:
            with Database(db_path) as db:
                db.init_schema()
                import_vcf(vcf_path, db, mode="replace", require_confirm=False)
                rows = db.conn.execute(
                    "SELECT fn, fn_pinyin FROM contacts ORDER BY fn_pinyin"
                ).fetchall()
                self.assertEqual([row["fn"] for row in rows], ["李四", "王五"])
                self.assertEqual(rows[0]["fn_pinyin"], "lisi")
                self.assertEqual(rows[1]["fn_pinyin"], "wangwu")
        finally:
            db_path.unlink(missing_ok=True)
            vcf_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
