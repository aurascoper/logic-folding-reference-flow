#!/usr/bin/env python3
"""PostToolUse dispatcher — run every static logic-folding guard on the repo.

Wired as a PostToolUse hook on Edit|Write|MultiEdit (see .claude/settings.json).
Exits 2 with violations on stderr so Claude Code surfaces them to the agent.
The evidence-forensics guard is a separate Stop hook (it reads the transcript).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import guard_eq2_divergence
import guard_fs_units
import guard_no_invented_yield
import guard_no_phantom_pyo3
import guard_path_segments

_STATIC_GUARDS = (
    guard_no_phantom_pyo3,
    guard_path_segments,
    guard_fs_units,
    guard_eq2_divergence,
    guard_no_invented_yield,
)


def main() -> int:
    violations: list[str] = []
    for g in _STATIC_GUARDS:
        try:
            violations.extend(g.find_violations())
        except Exception as e:  # never let a guard bug block a legitimate edit
            print(f"GUARD (skipped — internal error in {g.__name__}): {e}", file=sys.stderr)
    for v in violations:
        print(f"GUARD: {v}", file=sys.stderr)
    if violations:
        print(
            f"\n{len(violations)} logic-folding guard violation(s) — a documented "
            f"falsifiability constraint may have been dropped. See above.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
