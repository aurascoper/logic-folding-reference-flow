#!/usr/bin/env python3
"""Guard (evidence-forensics) — a test-success claim needs a real test run.

This is the deterministic form of the Phase-3 "evidence-forensics" judge lens:
a claim that tests pass must be backed by an actual test-invocation earlier in
the same transcript. Catches the claimed-but-unrun-verification hallucination.

Designed as a Stop / PostToolUse hook: Claude Code passes a JSON payload on
stdin containing `transcript_path`; we scan the assistant text. For unit tests,
pass `--text "<blob>"`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_SUCCESS_RE = re.compile(
    r"\b(all\s+green|tests?\s+pass(?:ed)?|\d+\s+passed|suite\s+is\s+green|green\s+across)\b",
    re.I,
)
_RUN_RE = re.compile(
    r"\b(pytest|cargo\s+test|npm\s+test|go\s+test|maturin\s+develop|python\s+-m\s+pytest|julia\s+.*\btest)\b",
    re.I,
)


def find_violations(text: str) -> list[str]:
    claims = list(_SUCCESS_RE.finditer(text))
    if not claims:
        return []
    runs = list(_RUN_RE.finditer(text))
    first_run = runs[0].start() if runs else None
    out: list[str] = []
    for c in claims:
        if first_run is None or first_run > c.start():
            out.append(
                f"offset {c.start()}: success claim {c.group(0)!r} with no preceding "
                f"test-run command (pytest / cargo test / ...) — possible "
                f"claimed-but-unrun verification (evidence)"
            )
    return out


def _read_input(argv: list[str]) -> str:
    if "--text" in argv:
        return argv[argv.index("--text") + 1]
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw  # treat as plain text
    tp = payload.get("transcript_path")
    if tp and Path(tp).exists():
        return Path(tp).read_text(errors="ignore")
    return raw


def main(argv: list[str]) -> int:
    text = _read_input(argv)
    v = find_violations(text)
    for f in v:
        print(f"GUARD-EVIDENCE: {f}", file=sys.stderr)
    # exit 2 surfaces the message back to the agent as feedback in a Stop hook
    return 2 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
