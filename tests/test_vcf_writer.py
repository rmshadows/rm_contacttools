import unittest

from contacttools.models.contact import Contact
from contacttools.vcf.writer import contact_to_lines


class VcfWriterNameTest(unittest.TestCase):
    def test_write_split_name(self):
        contact = Contact(
            fn="福彬 张",
            n_family="张",
            n_given="福彬",
            phones=[],
        )
        lines = contact_to_lines(contact)
        self.assertIn("FN:福彬 张", lines)
        self.assertIn("N:张;福彬;;;", lines)


if __name__ == "__main__":
    unittest.main()
