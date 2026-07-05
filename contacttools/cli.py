from __future__ import annotations

import argparse
import sys
from pathlib import Path

from contacttools.ops.export_vcf import export_vcf
from contacttools.ops.import_vcf import import_vcf
from contacttools.ops.merge import find_duplicate_groups, merge_contacts
from contacttools.ops.reset import reset_database
from contacttools.store.database import DEFAULT_DB_PATH, Database


def _cmd_init(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with Database(db_path) as db:
        db.init_schema()
    print(f"已初始化数据库: {db_path}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with Database(db_path) as db:
        db.init_schema()
        result = import_vcf(
            args.vcf, db, mode=args.mode, require_confirm=not args.yes
        )
    if result.get("cancelled"):
        print("已取消。数据库未修改。")
        return 0
    print(
        f"导入完成: 解析 {result['parsed']} 条, "
        f"写入 {result['saved']} 条, 跳过 {result['skipped']} 条, "
        f"库内共 {result['total_in_db']} 条"
    )
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with Database(db_path) as db:
        result = export_vcf(db, args.output)
    print(f"已导出 {result['count']} 条 -> {result['file']}")
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with Database(db_path) as db:
        db.init_schema()
        total = db.count_contacts()
        dups = db.duplicate_phone_report()
    print(f"联系人: {total} 条")
    print(f"重复号码组: {len(dups)} 组")
    for row in dups[:20]:
        print(f"  {row['number']} -> {row['contact_count']} 人 ({row['contact_ids']})")
    if len(dups) > 20:
        print(f"  ... 还有 {len(dups) - 20} 组")
    return 0


def _cmd_dedup(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with Database(db_path) as db:
        groups = find_duplicate_groups(db)
    if not groups:
        print("未发现重复号码")
        return 0
    print(f"发现 {len(groups)} 组重复号码:\n")
    for group in groups:
        names = ", ".join(c.fn for c in group["contacts"])
        ids = ", ".join(c.id for c in group["contacts"])
        print(f"  {group['number']} ({group['count']} 人): {names}")
        print(f"    id: {ids}\n")
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with Database(db_path) as db:
        try:
            kept = merge_contacts(
                db, args.keep, args.drop, require_confirm=not args.yes
            )
        except RuntimeError as e:
            print(e)
            return 1
    print(f"已合并到: {kept.fn} ({kept.id}), 剩余号码 {len(kept.phones)} 个")
    return 0


def _cmd_reset(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    result = reset_database(
        db_path,
        require_confirm=not args.yes,
        clear_reports=not args.keep_reports,
    )
    if result.get("already_empty"):
        print(f"数据库不存在: {db_path}（已是空状态）")
        return 0
    if result.get("cancelled"):
        print("已取消。数据库未修改。")
        return 0
    print(f"已重置。清空了 {result['cleared_contacts']} 条联系人。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contacttools",
        description="通讯录整理工具（SQLite + VCF，配合 LibreOffice Base 可视化编辑）",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite 数据库路径（默认: {DEFAULT_DB_PATH}）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="初始化 SQLite 数据库")
    p_init.set_defaults(func=_cmd_init)

    p_reset = sub.add_parser("reset", help="清空数据库，从头开始")
    p_reset.add_argument(
        "-y", "--yes", action="store_true", help="跳过确认（慎用）"
    )
    p_reset.add_argument(
        "--keep-reports",
        action="store_true",
        help="保留 data/review_warnings.txt",
    )
    p_reset.set_defaults(func=_cmd_reset)

    p_import = sub.add_parser("import", help="从 VCF 导入到 SQLite")
    p_import.add_argument("vcf", help="VCF 文件路径")
    p_import.add_argument(
        "--mode",
        choices=["replace", "append", "upsert"],
        default="replace",
        help="replace=清空后导入, append=仅新增, upsert=按号码更新",
    )
    p_import.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="跳过写库确认（慎用）",
    )
    p_import.set_defaults(func=_cmd_import)

    p_export = sub.add_parser("export", help="从 SQLite 导出 VCF（模板格式）")
    p_export.add_argument(
        "-o", "--output", required=True, help="输出 VCF 文件路径"
    )
    p_export.set_defaults(func=_cmd_export)

    p_stats = sub.add_parser("stats", help="数据库统计")
    p_stats.set_defaults(func=_cmd_stats)

    p_dedup = sub.add_parser("dedup", help="列出重复号码")
    p_dedup.set_defaults(func=_cmd_dedup)

    p_merge = sub.add_parser("merge", help="合并联系人")
    p_merge.add_argument("--keep", required=True, help="保留的联系人 id")
    p_merge.add_argument("--drop", nargs="+", required=True, help="被合并删除的 id")
    p_merge.add_argument(
        "-y", "--yes", action="store_true", help="跳过写库确认（慎用）"
    )
    p_merge.set_defaults(func=_cmd_merge)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
