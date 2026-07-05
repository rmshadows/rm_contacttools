import unittest
from pathlib import Path
from unittest.mock import patch

from contacttools.models.contact import Contact, Phone
from contacttools.ops.confirm import confirm_plan_with_report
from contacttools.ops.plan import build_import_plan
from contacttools.store.database import Database

ROOT = Path(__file__).resolve().parents[1]


class ImportPlanPreviewTest(unittest.TestCase):
    def test_append_shows_all_inserts_in_full_report(self):
        db_path = ROOT / "data" / "test_plan_preview.sqlite"
        db_path.unlink(missing_ok=True)
        try:
            with Database(db_path) as db:
                db.init_schema()
                db.save_contact(
                    Contact(fn="已有", phones=[Phone(number="10000000001")])
                )
                contacts = [
                    Contact(fn=f"新增{i}", phones=[Phone(number=f"2000000000{i}")])
                    for i in range(5)
                ] + [
                    Contact(fn="已有", phones=[Phone(number="10000000001")]),
                ]
                plan = build_import_plan(db, contacts, "append")
                full = plan.as_text()
                terminal = plan.terminal_summary()

                self.assertEqual(plan.insert_count, 5)
                self.assertEqual(plan.skip_count, 1)
                for i in range(5):
                    self.assertIn(f"新增{i}", full)
                self.assertIn("= 跳过  已有", full)
                self.assertNotIn("= 跳过  已有", terminal)
                self.assertIn("【将跳过】共 1 条（完整列表见预览文件）", terminal)
                insert_pos = full.index("【将新增】")
                skip_pos = full.index("【将跳过】")
                self.assertLess(insert_pos, skip_pos)
        finally:
            db_path.unlink(missing_ok=True)

    @patch("builtins.input", return_value="")
    def test_confirm_writes_preview_file(self, _mock_input):
        report = ROOT / "data" / "test_preview_report.txt"
        report.unlink(missing_ok=True)
        try:
            ok = confirm_plan_with_report(
                "full line 1\nfull line 2",
                "terminal summary",
                report,
                "测试",
            )
            self.assertFalse(ok)
            self.assertTrue(report.exists())
            self.assertEqual(report.read_text(encoding="utf-8"), "full line 1\nfull line 2")
        finally:
            report.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
