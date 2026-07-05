import unittest
from pathlib import Path

from contacttools.ops.export_vcf import export_vcf
from contacttools.ops.import_vcf import import_vcf
from contacttools.store.database import Database
from contacttools.vcf.parser import parse_vcf_file

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "templates" / "format_sample.vcf"
SAMPLE_COUNT = 3


class RoundtripTest(unittest.TestCase):
    def test_parse_sample(self):
        contacts = parse_vcf_file(SAMPLE)
        self.assertEqual(len(contacts), SAMPLE_COUNT)

    def test_import_export_roundtrip(self):
        db_path = ROOT / "data" / "test_roundtrip.sqlite"
        out_path = ROOT / "data" / "test_roundtrip.vcf"
        for p in (db_path, out_path):
            p.unlink(missing_ok=True)

        with Database(db_path) as db:
            db.init_schema()
            result = import_vcf(
                SAMPLE, db, mode="replace", require_confirm=False
            )
            self.assertEqual(result["parsed"], SAMPLE_COUNT)
            self.assertEqual(result["total_in_db"], SAMPLE_COUNT)

            export_vcf(db, out_path)
            reparsed = parse_vcf_file(out_path)
            self.assertEqual(len(reparsed), SAMPLE_COUNT)

        db_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
