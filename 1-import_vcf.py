#!/usr/bin/env python3
"""步骤 1：把手机导出的 VCF 导入 SQLite 数据库。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contacttools.ops.import_vcf import import_vcf
from contacttools.store.database import Database

# ========== 配置（按需修改）==========
# 手机导出的 VCF（默认 input/contacts.vcf）
INPUT_VCF = "input/contacts.vcf"

# 数据库路径（一般不用改）
DB_PATH = ROOT / "data" / "contacts.sqlite"

# 写库前确认；完整预览写入 data/import_preview.txt，终端只显示摘要
REQUIRE_CONFIRM = True

# 导入模式（三选一）：
#
# replace — 首次整理
#   清空 contacts.sqlite 后，将 VCF 全部写入。
#
# append — 第二次及以后（配合 3-dedup.py）
#   逐条与库中所有联系人比对内容（姓名、电话、邮箱、备注、单位等）：
#     · 与某条完全一致 → 跳过
#     · 任一字段不同 → 作为新记录写入（不修改、不合并已有行）
#   合并、保留哪条由步骤 3 人工处理（merge 或 DBeaver 删改）
#
# upsert — 以手机导出为准、同步已有联系人
#   逐条检查号码：
#     · 号码已在库中 → 合并进该条（保留原 id，见下方合并规则）
#     · 号码不在库中 → 新增
#   同号不会在库中产生两条，一般不必为同号再跑 merge。
#
# upsert 合并规则（号码匹配时，VCF 覆盖/补全库中记录）：
#   fn / org / note / url — VCF 非空则采用，否则保留库中值
#   电话、邮箱 — 合并列表，按号码/地址去重，不删库中已有项
#   photo — VCF 带头像则更新
#
# IMPORT_MODE = "replace"
IMPORT_MODE = "append"
# IMPORT_MODE = "upsert"

# 姓名解析（二选一）：
#
# split — 解析姓氏：FN 原样写入 fn；N 字段拆成 n_family（姓）、n_given（名）
#   例  FN:小明 张   N:张;小明;;;
#       → fn=小明 张,  n_family=张,  n_given=小明
#
# fullname — 不解析：FN 写入 fn；n_family 留空；n_given=fn
#   例  FN:小明 张
#       → fn=小明 张,  n_family=空,  n_given=小明 张
#
NAME_MODE = "split"
# NAME_MODE = "fullname"
# =====================================


def main() -> int:
    vcf_path = Path(INPUT_VCF)
    if not vcf_path.is_absolute():
        vcf_path = ROOT / vcf_path
    if not vcf_path.exists():
        print(f"找不到 VCF 文件: {vcf_path}")
        print("请先把手机导出的 .vcf 放到项目文件夹，并修改本脚本顶部的 INPUT_VCF。")
        return 1

    print("=" * 50)
    print("步骤 1 / 4  导入 VCF → SQLite")
    print("=" * 50)
    print(f"输入: {vcf_path}")
    print(f"数据库: {DB_PATH}")
    print(f"模式: {IMPORT_MODE}")
    print(f"姓名: {NAME_MODE}")
    print()

    with Database(DB_PATH) as db:
        db.init_schema()
        result = import_vcf(
            vcf_path,
            db,
            mode=IMPORT_MODE,
            name_mode=NAME_MODE,
            require_confirm=REQUIRE_CONFIRM,
        )

    if result.get("cancelled"):
        print("已取消。数据库未修改。")
        print(f"可查看预览: {(DB_PATH.parent / 'import_preview.txt').resolve()}")
        return 0

    print(f"解析: {result['parsed']} 条")
    print(f"写入: {result['saved']} 条")
    print(f"跳过: {result['skipped']} 条")
    print(f"库内合计: {result['total_in_db']} 条")
    print()
    print("下一步 → 运行  2-edit_in_dbeaver.py  或  2-edit_in_base.py  整理联系人")
    if IMPORT_MODE == "append":
        print("       append 模式：整理后请运行  3-dedup.py  处理同名与重复号码")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
