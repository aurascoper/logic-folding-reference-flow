"""Each guard: clean on the live repo, fires on a known-bad fixture.

Run: python/venv/bin/python -m pytest tools/guards/test_guards.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]

import guard_claimed_pass_has_command as g_ev
import guard_eq2_divergence as g_eq2
import guard_fs_units as g_fs
import guard_no_invented_yield as g_yield
import guard_no_phantom_pyo3 as g_pyo3
import guard_path_segments as g_seg


# --- the live repo's main tree is clean for every static guard ---
def test_clean_repo_pyo3():
    assert g_pyo3.find_violations(REPO) == []


def test_clean_repo_segments():
    assert g_seg.find_violations(REPO) == []


def test_clean_repo_fs():
    assert g_fs.find_violations(REPO) == []


def test_clean_repo_eq2():
    assert g_eq2.find_violations(REPO) == []


def test_clean_repo_yield():
    assert g_yield.find_violations(REPO) == []


# --- minimal throwaway repo skeleton (clean by construction) ---
def _mkrepo(tmp: Path) -> Path:
    (tmp / "python" / "src" / "logic_folding_reference").mkdir(parents=True)
    (tmp / "rust" / "src").mkdir(parents=True)
    (tmp / "docs").mkdir(parents=True)
    (tmp / "rust" / "Cargo.toml").write_text('[dependencies]\nrayon = "1"\n')
    (tmp / "docs" / "MEMO_INDEX.md").write_text(
        "Rust omits R_v*C_v / R_b*C_b self-loading; abbreviated form.\n"
    )
    (tmp / "rust" / "src" / "lib.rs").write_text(
        "// abbreviated; self-loading omitted\n"
        "let via = self.r_v * self.c_load + self.r_drv * self.c_v;\n"
    )
    return tmp


def _pkgfile(root: Path, name: str, body: str) -> None:
    (root / "python" / "src" / "logic_folding_reference" / name).write_text(body)


def test_pyo3_fires(tmp_path):
    r = _mkrepo(tmp_path)
    _pkgfile(r, "x.py", "import logic_folding_core\n")
    assert g_pyo3.find_violations(r)


def test_pyo3_ok_when_pyo3_present(tmp_path):
    r = _mkrepo(tmp_path)
    (r / "rust" / "Cargo.toml").write_text('[dependencies]\npyo3 = "0.28"\n')
    _pkgfile(r, "x.py", "import logic_folding_core\n")
    assert g_pyo3.find_violations(r) == []


def test_segments_fires(tmp_path):
    r = _mkrepo(tmp_path)
    _pkgfile(r, "x.py", "def f(path):\n    return [s for s in path.nodes]\n")
    assert g_seg.find_violations(r)


def test_fs_fires(tmp_path):
    r = _mkrepo(tmp_path)
    _pkgfile(r, "x.py", "def f(savings_fs):\n    return savings_fs > 50\n")
    assert g_fs.find_violations(r)


def test_fs_ok_with_proper_units(tmp_path):
    r = _mkrepo(tmp_path)
    _pkgfile(r, "x.py", "def f(savings_fs):\n    return savings_fs > 50_000\n")
    assert g_fs.find_violations(r) == []


def test_eq2_fires_on_added_selfloading(tmp_path):
    r = _mkrepo(tmp_path)
    (r / "rust" / "src" / "lib.rs").write_text(
        "let via = self.r_v * self.c_load + self.r_v * self.c_v;\n"
    )
    assert g_eq2.find_violations(r)


def test_eq2_fires_on_erased_provenance(tmp_path):
    r = _mkrepo(tmp_path)
    (r / "docs" / "MEMO_INDEX.md").write_text(
        "Full form, identical to the Python engine.\n"
    )
    assert g_eq2.find_violations(r)


def test_eq2_sentinel_waives(tmp_path):
    r = _mkrepo(tmp_path)
    (r / "rust" / "src" / "lib.rs").write_text(
        "// EQ2-DIVERGENCE-CHANGE-APPROVED: memo v4.1 eq:breakeven\n"
        "let via = self.r_v * self.c_v;\n"
    )
    assert g_eq2.find_violations(r) == []


def test_yield_fires(tmp_path):
    r = _mkrepo(tmp_path)
    _pkgfile(r, "value_score.py", "stacked_die_yield = 0.85\n")
    assert g_yield.find_violations(r)


def test_evidence_fires_on_unbacked_claim():
    assert g_ev.find_violations("I made the change. All tests pass now.")


def test_evidence_ok_when_command_present():
    assert not g_ev.find_violations(
        "I ran pytest -q\n45 passed in 0.2s\nSo the tests pass."
    )
