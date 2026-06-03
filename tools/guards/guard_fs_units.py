#!/usr/bin/env python3
"""Guard V2 (HEURISTIC) — femtosecond/picosecond unit boundary.

A delay quantity named `*_fs` compared against a bare picosecond-magnitude
literal (0 < x < 1000) is almost certainly a ps/fs unit error: 50 ps must be
written 50_000 fs, not 50. Catches the Task-C landmine (`savings_fs > 50`).

This is explicitly HEURISTIC — it can miss conversions hidden behind a variable
and can in principle over-flag a genuinely-fs sub-1000 threshold. It is logged
as heuristic so a real sub-1000 fs bound can be waived deliberately rather than
silently. (No silent cap.)
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_fs_operand(n: ast.AST) -> bool:
    if isinstance(n, ast.Name):
        return n.id.endswith("_fs")
    if isinstance(n, ast.Attribute):
        return n.attr.endswith("_fs")
    return False


def find_violations(root: Path = REPO_ROOT) -> list[str]:
    pkg = root / "python" / "src" / "logic_folding_reference"
    if not pkg.exists():
        return []
    out: list[str] = []
    for py in pkg.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            operands = [node.left, *node.comparators]
            if not any(_is_fs_operand(o) for o in operands):
                continue
            for o in operands:
                if (
                    isinstance(o, ast.Constant)
                    and isinstance(o.value, (int, float))
                    and not isinstance(o.value, bool)
                    and 0 < o.value < 1000
                ):
                    out.append(
                        f"{py.relative_to(root)}:{node.lineno}: a *_fs quantity is "
                        f"compared to bare literal {o.value!r} (<1000) — likely ps/fs "
                        f"unit error; 50 ps == 50_000 fs (V2, heuristic)"
                    )
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else REPO_ROOT
    v = find_violations(root)
    for f in v:
        print(f"GUARD-V2 VIOLATION: {f}", file=sys.stderr)
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
