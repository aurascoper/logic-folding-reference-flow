#!/usr/bin/env python3
"""Guard V5 — no phantom PyO3 bridge.

Fires if Python imports `logic_folding_core` (the planned Rust extension) while
`rust/Cargo.toml` has no `pyo3` dependency: i.e. the agent referenced an
unbuilt capability. Deterministic — the import either resolves to a real
extension (pyo3 present) or it does not.

Maps to the Phase-4 vulnerability V5 ("planned, not present"). On the current
`main` there is no such import and no pyo3, so this guard passes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPORT_RE = re.compile(
    r"^\s*(?:import\s+logic_folding_core|from\s+logic_folding_core\s+import)", re.M
)
_SKIP = ("/venv/", "/.venv/", "site-packages", "/target/", "/build/")


def find_violations(root: Path = REPO_ROOT) -> list[str]:
    cargo = root / "rust" / "Cargo.toml"
    has_pyo3 = cargo.exists() and "pyo3" in cargo.read_text(errors="ignore")
    if has_pyo3:
        return []  # the bridge actually exists; the import is legitimate
    py_root = root / "python"
    if not py_root.exists():
        return []
    out: list[str] = []
    for py in py_root.rglob("*.py"):
        s = str(py)
        if any(k in s for k in _SKIP):
            continue
        text = py.read_text(errors="ignore")
        for m in _IMPORT_RE.finditer(text):
            line = text[: m.start()].count("\n") + 1
            out.append(
                f"{py.relative_to(root)}:{line}: imports logic_folding_core but "
                f"rust/Cargo.toml has no pyo3 dependency (phantom PyO3 bridge — V5)"
            )
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else REPO_ROOT
    v = find_violations(root)
    for f in v:
        print(f"GUARD-V5 VIOLATION: {f}", file=sys.stderr)
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
