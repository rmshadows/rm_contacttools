from __future__ import annotations

from pathlib import Path


def ask_confirm(message: str, *, default: bool = False) -> bool:
    """
    终端确认。默认 N（不执行），输入 y/是 才继续。
    非交互环境（无 stdin）视为取消。
    """
    suffix = "[y/N]" if not default else "[Y/n]"
    try:
        answer = input(f"{message} {suffix} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        return False

    if not answer:
        return default
    return answer in ("y", "yes", "是", "好", "确认")


def confirm_or_cancel(plan_text: str, action: str) -> bool:
    print(plan_text)
    print()
    return ask_confirm(f"确认执行「{action}」并写入数据库？")


def confirm_plan_with_report(
    full_text: str,
    terminal_text: str,
    report_path: Path,
    action: str,
) -> bool:
    """完整预览写入 report_path；终端只显示 terminal_text。"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(full_text, encoding="utf-8")
    print(terminal_text)
    print()
    print(f"完整预览: {report_path.resolve()}")
    print()
    return ask_confirm(f"确认执行「{action}」并写入数据库？")
