#!/usr/bin/env python3
"""步骤 4：从 SQLite 导出 VCF（模板格式），复制到手机导入。"""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.ops.export_vcf import export_vcf
from contacttools.store.database import Database

# ========== 配置（按需修改）==========
DB_PATH = ROOT / "data" / "contacts.sqlite"

# 导出文件名（留空则自动生成 contacts_YYYYMMDD_HHMMSS.vcf）
OUTPUT_VCF = ""

# 固定文件名示例: OUTPUT_VCF = "contacts_export.vcf"
# =====================================


def main() -> int:
    print("=" * 50)
    print("步骤 4 / 4  导出 VCF → 复制到手机")
    print("=" * 50)

    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        print("请先运行  1-import_vcf.py")
        return 1

    if OUTPUT_VCF:
        out_path = ROOT / OUTPUT_VCF
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = ROOT / f"contacts_{stamp}.vcf"

    with Database(DB_PATH) as db:
        db.init_schema()
        total = db.count_contacts()
        if total == 0:
            print("数据库里没有联系人，请先导入。")
            return 1
        result = export_vcf(db, out_path)

    print(f"已导出: {result['count']} 条")
    print(f"文件: {out_path.resolve()}")
    print()
    print("【导入手机】")
    print("1. 把上面的 .vcf 文件传到手机（数据线 / 微信 / 网盘均可）")
    print("2. 用手机「联系人 → 导入」选择该 VCF 文件")
    print("3. 若提示重复，选「跳过」或「覆盖」（视手机选项而定）")
    print("4. 建议先导少量测试；确认无误后再导全量")
    print()
    print("导出格式参照: contacts_20260613_094900.vcf  (vCard 4.0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
