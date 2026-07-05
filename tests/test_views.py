import unittest
from pathlib import Path

from contacttools.store.database import Database

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_VIEWS = (
    "v_contacts_wide",
    "v_contacts_full",
    "v_duplicate_phones",
    "v_duplicate_phone_detail",
)


class ViewsTest(unittest.TestCase):
    def test_views_created_on_init(self):
        db_path = ROOT / "data" / "test_views.sqlite"
        db_path.unlink(missing_ok=True)
        try:
            with Database(db_path) as db:
                db.init_schema()
                names = {
                    row[0]
                    for row in db.conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='view'"
                    ).fetchall()
                }
                for name in EXPECTED_VIEWS:
                    self.assertIn(name, names)

                db.conn.execute(
                    """
                    INSERT INTO contacts (id, fn, fn_pinyin, n_given)
                    VALUES ('c1', '甲', 'jia', '甲')
                    """
                )
                db.conn.execute(
                    """
                    INSERT INTO phones (contact_id, number, types, pref, sort_order)
                    VALUES ('c1', '100', 'CELL', 0, 0),
                           ('c1', '200', 'HOME', 0, 1),
                           ('c1', '300', 'WORK', 0, 2),
                           ('c1', '400', 'FAX', 0, 3),
                           ('c1', '500', 'CELL', 0, 4),
                           ('c1', '600', 'CELL', 0, 5)
                    """
                )
                db.conn.commit()

                full = db.conn.execute(
                    "SELECT phones, phone_count FROM v_contacts_full WHERE id='c1'"
                ).fetchone()
                self.assertEqual(full["phone_count"], 6)
                self.assertIn("600", full["phones"])
                self.assertIn("100", full["phones"])
        finally:
            db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
