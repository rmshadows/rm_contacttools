import unittest

from contacttools.vcf.parser import parse_vcf_text
from contacttools.vcf.writer import contacts_to_vcf_text


class TelTypeParseTest(unittest.TestCase):
    def test_quoted_home_fax(self):
        text = """BEGIN:VCARD
VERSION:4.0
FN:test
TEL;TYPE="HOME;FAX":01012345678
END:VCARD"""
        phones = parse_vcf_text(text)[0].phones
        self.assertEqual(phones[0].types, ["HOME", "FAX"])

    def test_separate_work_fax_params(self):
        text = """BEGIN:VCARD
VERSION:4.0
FN:test
TEL;TYPE=WORK;TYPE=FAX:01087654321
END:VCARD"""
        phones = parse_vcf_text(text)[0].phones
        self.assertEqual(phones[0].types, ["WORK", "FAX"])

    def test_custom_type_with_pref(self):
        text = """BEGIN:VCARD
VERSION:4.0
FN:test
TEL;TYPE=热线,PREF=1:4007006600
END:VCARD"""
        phone = parse_vcf_text(text)[0].phones[0]
        self.assertEqual(phone.types, ["热线"])
        self.assertTrue(phone.pref)

    def test_roundtrip_multi_type(self):
        original = """BEGIN:VCARD
VERSION:4.0
FN:示例机构
TEL;TYPE=HOME:01011112222
TEL;TYPE="WORK;FAX":01087654321
END:VCARD"""
        contact = parse_vcf_text(original)[0]
        exported = contacts_to_vcf_text([contact])
        again = parse_vcf_text(exported)[0]
        self.assertEqual(
            again.phones[1].types,
            contact.phones[1].types,
        )
        self.assertIn('TYPE="WORK;FAX"', exported)


if __name__ == "__main__":
    unittest.main()
