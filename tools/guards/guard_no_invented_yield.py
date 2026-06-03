#!/usr/bin/env python3
"""Guard V6 — no invented stacked-die yield / C_good literal.

Stacked-die yield and inter-wafer variation are *deliberately unmodeled* (memo
Trigger B has not fired); the README calls inventing them "a slider over invented
data". This guard flags any numeric literal bound to (or passed as) a
yield / C_good quantity in the package — the Task-B failure mode.

On current `main` there is no Eq.5 / value-score code, so it passes.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_NAMES = ("yield", "c_good", "cgood", "good_die", "bonding_yield", "die_yield")


def _hit(name: str | None) -> bool:
    if not name:
        return False
    n = name.lower()
    return any(k in n for k in _NAMES)


def _numeric(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    )


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
        rel = py.relative_to(root)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and _hit(t.id) and _numeric(node.value):
                        out.append(
                            f"{rel}:{node.lineno}: numeric literal assigned to "
                            f"'{t.id}' — stacked-die yield/C_good is deliberately "
                            f"unmodeled (Trigger B); supply as operator input (V6)"
                        )
            elif isinstance(node, ast.AnnAssign):
                if (
                    isinstance(node.target, ast.Name)
                    and _hit(node.target.id)
                    and node.value is not None
                    and _numeric(node.value)
                ):
                    out.append(
                        f"{rel}:{node.lineno}: default numeric for "
                        f"'{node.target.id}' — yield/C_good must not have an "
                        f"invented default (V6)"
                    )
            elif isinstance(node, ast.Call):
                for kw in node.keywords:
                    if _hit(kw.arg) and _numeric(kw.value):
                        out.append(
                            f"{rel}:{node.lineno}: literal passed as '{kw.arg}=' "
                            f"— invented yield/C_good (V6)"
                        )
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else REPO_ROOT
    v = find_violations(root)
    for f in v:
        print(f"GUARD-V6 VIOLATION: {f}", file=sys.stderr)
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
