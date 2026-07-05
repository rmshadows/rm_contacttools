import unittest
from pathlib import Path

from contacttools.models.contact import Contact, Phone
from contacttools.ops.plan import build_import_plan
from contacttools.store.database import Database

ROOT = Path(__file__).resolve().parents[1]


class ConfirmPlanTest(unittest.TestCase):
    def test_replace_plan_shows_delete(self):
        db_path = ROOT / "data" / "test_confirm.sqlite"
        db_path.unlink(missing_ok=True)
        with Database(db_path) as db:
            db.init_schema()
            c = Contact(fn="测试", phones=[Phone(number="13800000000")])
            db.save_contact(c)
            plan = build_import_plan(
                db,
                [Contact(fn="新联系人", phones=[Phone(number="13900000000")])],
                "replace",
            )
            text = plan.as_text()
            self.assertIn("将删除现有记录: 1 条", text)
            self.assertIn("新增", text)
        db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
