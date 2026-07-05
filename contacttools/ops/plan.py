from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from contacttools.models.contact import Contact
from contacttools.ops.diff import (
    copy_contact,
    diff_contact_fields,
    find_identical_contact,
    summarize_delete,
    summarize_new,
    summarize_update,
)
from contacttools.ops.contact_merge import merge_contact_fields
from contacttools.store.database import Database

ImportMode = Literal["replace", "append", "upsert"]
DEFAULT_TERMINAL_INSERT_LINES = 50


@dataclass
class ImportPlan:
    mode: ImportMode
    parsed: int
    insert_lines: list[str] = field(default_factory=list)
    update_lines: list[str] = field(default_factory=list)
    skip_lines: list[str] = field(default_factory=list)
    notice_lines: list[str] = field(default_factory=list)
    insert_count: int = 0
    update_count: int = 0
    skip_count: int = 0
    delete_count: int = 0

    def as_text(self) -> str:
        header = [
            "【数据库变更预览 — 尚未写入】",
            f"模式: {self.mode}",
            f"VCF 解析: {self.parsed} 条",
        ]
        if self.delete_count:
            header.append(f"将删除现有记录: {self.delete_count} 条")
        header.append(
            f"将新增: {self.insert_count}  将更新: {self.update_count}  将跳过: {self.skip_count}"
        )
        header.append("")

        if self.notice_lines:
            header.extend(self.notice_lines)
            header.append("")

        has_detail = (
            self.insert_lines or self.update_lines or self.skip_lines or self.notice_lines
        )
        if not has_detail and not self.delete_count:
            header.append("  (无变更)")
            return "\n".join(header)

        if self.insert_lines:
            header.append(f"【将新增】共 {self.insert_count} 条")
            header.extend(self.insert_lines)
            header.append("")

        if self.update_lines:
            header.append(f"【将更新】共 {self.update_count} 条")
            header.extend(self.update_lines)
            header.append("")

        if self.skip_lines:
            header.append(f"【将跳过】共 {self.skip_count} 条")
            header.extend(self.skip_lines)

        return "\n".join(header).rstrip()

    def terminal_summary(
        self, *, max_insert_lines: int = DEFAULT_TERMINAL_INSERT_LINES
    ) -> str:
        """终端摘要：新增尽量列全；跳过/更新仅统计（详情见预览文件）。"""
        header = [
            "【数据库变更预览 — 尚未写入】",
            f"模式: {self.mode}",
            f"VCF 解析: {self.parsed} 条",
        ]
        if self.delete_count:
            header.append(f"将删除现有记录: {self.delete_count} 条")
        header.append(
            f"将新增: {self.insert_count}  将更新: {self.update_count}  将跳过: {self.skip_count}"
        )
        header.append("")

        if self.notice_lines:
            header.extend(self.notice_lines)
            header.append("")

        if self.insert_lines:
            header.append(f"【将新增】共 {self.insert_count} 条")
            shown = self.insert_lines[:max_insert_lines]
            header.extend(shown)
            if len(self.insert_lines) > max_insert_lines:
                rest = len(self.insert_lines) - max_insert_lines
                header.append(f"  … 还有 {rest} 条新增，见完整预览文件")
            header.append("")

        if self.update_lines:
            header.append(f"【将更新】共 {self.update_count} 条（详情见完整预览文件）")
            header.append("")

        if self.skip_lines:
            header.append(f"【将跳过】共 {self.skip_count} 条（完整列表见预览文件）")

        if (
            not self.insert_lines
            and not self.update_lines
            and not self.skip_lines
            and not self.notice_lines
            and not self.delete_count
        ):
            header.append("  (无变更)")

        return "\n".join(header).rstrip()


def build_import_plan(
    db: Database, contacts: list[Contact], mode: ImportMode
) -> ImportPlan:
    plan = ImportPlan(mode=mode, parsed=len(contacts))

    if mode == "replace":
        plan.delete_count = db.count_contacts()
        if plan.delete_count:
            plan.notice_lines.append(
                f"  ! 清空数据库现有 {plan.delete_count} 条联系人"
            )
        for contact in contacts:
            plan.insert_lines.append(summarize_new(contact))
            plan.insert_count += 1
        return plan

    if mode == "append":
        for contact in contacts:
            identical = find_identical_contact(db, contact)
            if identical:
                plan.skip_lines.append(
                    f"  = 跳过  {contact.fn}  "
                    f"(与库中 {identical.fn} id {identical.id[:8]}… 内容完全一致)"
                )
                plan.skip_count += 1
            else:
                plan.insert_lines.append(
                    summarize_new(contact, note="与库中无完全一致记录，作为新条写入")
                )
                plan.insert_count += 1
        return plan

    for contact in contacts:
        numbers = [p.number for p in contact.phones if p.number]
        existing_ids: set[str] = set()
        for n in numbers:
            existing_ids.update(db.find_contact_ids_by_phone(n))
        if existing_ids:
            keep_id = sorted(existing_ids)[0]
            existing = db.get_contact(keep_id)
            if existing:
                before = copy_contact(existing)
                merged = merge_contact_fields(copy_contact(existing), copy_contact(contact))
                changes = diff_contact_fields(before, merged)
                plan.update_lines.append(summarize_update(existing.fn, keep_id, changes))
                plan.update_count += 1
            else:
                plan.insert_lines.append(summarize_new(contact))
                plan.insert_count += 1
        else:
            plan.insert_lines.append(summarize_new(contact))
            plan.insert_count += 1

    return plan


@dataclass
class MergePlan:
    keep_id: str
    keep_fn: str
    drop_ids: list[str]
    lines: list[str] = field(default_factory=list)
    delete_count: int = 0

    def as_text(self) -> str:
        header = [
            "【合并变更预览 — 尚未写入】",
            f"保留: {self.keep_fn}  (id {self.keep_id[:8]}…)",
            f"将删除: {self.delete_count} 条联系人",
            "",
        ]
        return "\n".join(header + (self.lines or ["  (无变更)"]))


def build_merge_plan(db: Database, keep_id: str, drop_ids: list[str]) -> MergePlan:
    from contacttools.ops.merge import simulate_merge

    kept, deleted, change_lines = simulate_merge(db, keep_id, drop_ids)
    plan = MergePlan(
        keep_id=keep_id,
        keep_fn=kept.fn,
        drop_ids=[d for d in drop_ids if d != keep_id],
        delete_count=len(deleted),
    )
    for name, cid in deleted:
        plan.lines.append(f"  - 删除  {name}  (id {cid[:8]}…)")
    if change_lines:
        plan.lines.append(f"  ~ 保留记录变更 ({kept.fn}):")
        plan.lines.extend(change_lines)
    else:
        plan.lines.append("  ~ 保留记录字段无变化（仅删除重复条目）")
    return plan
