"""VCF 4.0 模板规范 — 参照 templates/format_sample.vcf"""

VERSION = "4.0"
PRODID = "ez-vcard 0.12.1"

# 导出字段顺序（有值才写，TITLE 在 ORG 存在时即使为空也写）
# 姓名：FN=全名，N:;全名;;;（姓段留空）
FIELD_ORDER = (
    "VERSION",
    "PRODID",
    "FN",
    "N",
    "TEL",
    "NOTE",
    "URL",
    "ORG",
    "TITLE",
    "EMAIL",
    "PHOTO",
)

MAX_LINE_LENGTH = 75
PHOTO_MIME = "image/jpeg"
