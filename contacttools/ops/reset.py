from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from contacttools.store.database import Database


@dataclass
class ResetPlan:
    db_path: Path
    contact_count: int
    phone_count: int
    import_batches: int
    merge_history: int
    extra_files: list[Path]

    def as_text(self) -> str:
        lines = [
            "【重置预览 — 尚未执行】",
            f"数据库: {self.db_path.resolve()}",
            "",
            "将清空:",
            f"  联系人: {self.contact_count} 条",
            f"  电话记录: {self.phone_count} 条",
            f"  导入历史: {self.import_batches} 条",
            f"  合并历史: {self.merge_history} 条",
        ]
        if self.extra_files:
            lines.append("")
            lines.append("将删除辅助文件:")
            for p in self.extra_files:
                lines.append(f"  - {p.resolve()}")
        lines.extend(
            [
                "",
                "重置后数据库为空，需重新运行  1-import_vcf.py  导入。",
                "（不会删除 VCF 源文件、legacy/、模板文件）",
            ]
        )
        return "\n".join(lines)


def _count_table(db: Database, table: str) -> int:
    try:
        row = db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])
    except Exception:
        return 0


def build_reset_plan(
    db: Database,
    *,
    data_dir: Path | None = None,
    clear_reports: bool = True,
) -> ResetPlan:
    data_dir = data_dir or db.path.parent
    extra: list[Path] = []
    if clear_reports:
        for name in ("review_warnings.txt", "import_preview.txt", "add_contact_preview.txt"):
            report = data_dir / name
            if report.exists():
                extra.append(report)

    return ResetPlan(
        db_path=db.path,
        contact_count=db.count_contacts(),
        phone_count=_count_table(db, "phones"),
        import_batches=_count_table(db, "import_batches"),
        merge_history=_count_table(db, "merge_history"),
        extra_files=extra,
    )


def reset_database(
    db_path: Path | str,
    *,
    require_confirm: bool = True,
    clear_reports: bool = True,
) -> dict:
    from contacttools.ops.confirm import confirm_or_cancel

    db_path = Path(db_path)
    data_dir = db_path.parent

    if not db_path.exists():
        return {
            "cancelled": False,
            "db_path": str(db_path),
            "cleared_contacts": 0,
            "total_in_db": 0,
            "already_empty": True,
        }

    with Database(db_path) as db:
        db.init_schema()
        plan = build_reset_plan(db, data_dir=data_dir, clear_reports=clear_reports)
        if require_confirm:
            if not confirm_or_cancel(plan.as_text(), "重置数据库"):
                return {"cancelled": True, "db_path": str(db_path)}

    for suffix in ("", "-wal", "-shm"):
        p = Path(f"{db_path}{suffix}")
        if p.exists():
            p.unlink()

    for extra in plan.extra_files:
        extra.unlink(missing_ok=True)

    with Database(db_path) as fresh:
        fresh.init_schema()
        total = fresh.count_contacts()

    return {
        "cancelled": False,
        "db_path": str(db_path),
        "cleared_contacts": plan.contact_count,
        "total_in_db": total,
    }
