#!/usr/bin/env python3
"""Guard V8 — path elements are `.segments`, not `.nodes`.

The timing-path objects expose `.segments` (list of WireSegment, each with
`.is_wire` / `.incr_delay_fs`). A `.nodes` attribute access inside the package
is the documented hallucinated field name. AST-based, scoped to the package, so
it does not false-positive on unrelated `.nodes` elsewhere.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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
            if isinstance(node, ast.Attribute) and node.attr == "nodes":
                out.append(
                    f"{py.relative_to(root)}:{node.lineno}: '.nodes' access — path "
                    f"elements are '.segments' (WireSegment, .is_wire/.incr_delay_fs), "
                    f"not '.nodes' (V8)"
                )
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else REPO_ROOT
    v = find_violations(root)
    for f in v:
        print(f"GUARD-V8 VIOLATION: {f}", file=sys.stderr)
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
