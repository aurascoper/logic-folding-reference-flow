#!/usr/bin/env bash
# flows/run_live.sh — run both recipes + the contract check in one command.
#
# Run from the OpenROAD-flow-scripts `flow/` directory, with `openroad` on PATH
# (after a local build: `source ../env.sh`). One short command instead of three
# long ones:
#
#   cd /workspaces/OpenROAD-flow-scripts/flow
#   bash ~/lf/flows/run_live.sh
#
# Overridable: ORFS_FLOW (default $PWD), PDK (sky130hd), DESIGN (gcd).
# Writes checks.json / netlen.json + logs into the flow dir; prints the
# 4-part-gate result. Timing-only if no routed .def is found yet.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../lf/flows
REPO="$(dirname "$HERE")"                              # .../lf
FLOW="${ORFS_FLOW:-$PWD}"
PDK="${PDK:-sky130hd}"
DESIGN="${DESIGN:-gcd}"

LEFDIR="$FLOW/platforms/$PDK/lef"
RES="$FLOW/results/$PDK/$DESIGN/base"
TLEF="$(ls "$LEFDIR"/*.tlef 2>/dev/null | head -1 || true)"
MLEF="$(ls "$LEFDIR"/*merged*.lef 2>/dev/null | head -1 || ls "$LEFDIR"/*.lef 2>/dev/null | head -1 || true)"
DEF="$(ls "$RES"/6_final.def 2>/dev/null | head -1 || ls "$RES"/*route*.def 2>/dev/null | tail -1 || true)"

if ! command -v openroad >/dev/null 2>&1; then
  echo "ERROR: 'openroad' not on PATH. From the ORFS root run: source ./env.sh" >&2
  exit 1
fi
cd "$FLOW"

echo "== [1/3] timing dump -> checks.json =="
openroad -no_init -exit "$HERE/sta_dump.tcl" > checks.json 2> sta_dump.log \
  || { echo "  sta_dump failed; tail of sta_dump.log:"; tail -n 15 sta_dump.log; exit 1; }

NETLEN_ARG=()
if [ -n "$DEF" ] && [ -f "$DEF" ] && [ -n "$TLEF" ]; then
  echo "== [2/3] geometry dump ($DEF) -> netlen.json =="
  openroad -python "$HERE/odb_wirelength.py" \
      --tlef "$TLEF" --lef "$MLEF" --def "$DEF" \
      --pdk "$PDK" --design "$DESIGN" > netlen.json 2> odb.log \
    && NETLEN_ARG=(netlen.json) \
    || { echo "  odb_wirelength failed; tail of odb.log:"; tail -n 15 odb.log; }
else
  echo "== [2/3] no routed .def under $RES yet -> timing-only check =="
fi

echo "== [3/3] contract check =="
PYTHONPATH="$REPO/python/src" python3 "$HERE/check_live.py" checks.json "${NETLEN_ARG[@]}"
