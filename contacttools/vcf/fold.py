from __future__ import annotations


def unfold_lines(text: str) -> list[str]:
    """合并 vCard 折行（续行以空格或 Tab 开头）。"""
    logical: list[str] = []
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith((" ", "\t")) and logical:
            logical[-1] += line[1:]
        else:
            logical.append(line)
    return logical


def fold_line(line: str, max_length: int = 75) -> list[str]:
    """按 vCard 规则折行（ASCII 内容）。"""
    if len(line) <= max_length:
        return [line]
    parts = [line[:max_length]]
    rest = line[max_length:]
    while rest:
        parts.append(" " + rest[: max_length - 1])
        rest = rest[max_length - 1 :]
    return parts
