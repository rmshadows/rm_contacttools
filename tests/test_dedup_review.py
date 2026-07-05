import unittest
from pathlib import Path

from contacttools.models.contact import Contact, Phone
from contacttools.ops.dedup_review import (
    find_exact_duplicate_groups,
    remove_exact_duplicates,
    run_dedup_review,
)
from contacttools.store.database import Database

ROOT = Path(__file__).resolve().parents[1]


class DedupReviewTest(unittest.TestCase):
    def test_find_exact_duplicate_groups(self):
        db_path = ROOT / "data" / "test_dedup_exact.sqlite"
        db_path.unlink(missing_ok=True)
        with Database(db_path) as db:
            db.init_schema()
            db.save_contact(Contact(fn="张三", phones=[Phone(number="13800000001")]))
            db.save_contact(Contact(fn="张三", phones=[Phone(number="13800000001")]))
            db.save_contact(Contact(fn="李四", phones=[Phone(number="13900000001")]))

            groups = find_exact_duplicate_groups(db)
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0].contacts), 2)
            self.assertEqual(len(groups[0].drop_ids), 1)

            removed = remove_exact_duplicates(db, groups, require_confirm=False)
            self.assertEqual(removed, 1)
            self.assertEqual(db.count_contacts(), 2)
        db_path.unlink(missing_ok=True)

    def test_same_name_not_exact(self):
        db_path = ROOT / "data" / "test_dedup_name.sqlite"
        db_path.unlink(missing_ok=True)
        with Database(db_path) as db:
            db.init_schema()
            db.save_contact(
                Contact(fn="王五", note="A", phones=[Phone(number="13700000001")])
            )
            db.save_contact(
                Contact(fn="王五", note="B", phones=[Phone(number="13700000002")])
            )
            review = run_dedup_review(db)
            self.assertEqual(len(review.exact_groups), 0)
            self.assertEqual(len(review.name_groups), 1)
        db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
