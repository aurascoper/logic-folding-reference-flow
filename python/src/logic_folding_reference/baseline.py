"""2D-baseline ingestion contract for the LogicFolding reference flow.

This module is the boundary between the *flat, planar 2D baseline* (produced by
OpenROAD / OpenSTA on a public PDK) and the path-level break-even engine in
:mod:`logic_folding_reference.core_solver` (memo §7, Eq. 2).

Per the memo, OpenROAD is the **2D baseline anchor**: it does flat 2D
place-and-route and static timing, and supplies the *left-hand side* of Eq. 2 —
the real horizontal wire length ``l_h`` and the horizontal delay a fold could
reclaim. The *right-hand side* (vertical via / bond parasitics, redundancy,
thermal derate) is the 3D tax and is supplied separately; it is not something a
2D tool can measure.

Rather than parse OpenSTA's version-specific native JSON, this flow defines its
own stable contract — schema ``logic-folding-baseline/v0`` — and makes the
OpenROAD Tcl recipe (``flows/sta_dump.tcl``) responsible for emitting it. The
parser here is therefore the only thing that must stay green in CI; the recipe
is the operator-run reproduction step (it needs OpenROAD + a PDK, which is the
memo's Trigger C).

Schema ``logic-folding-baseline/v0`` (one JSON object)::

    {
      "schema": "logic-folding-baseline/v0",
      "pdk": "sky130hd",
      "design": "gcd",
      "corner": "tt",
      "units": {"time": "ns", "resistance": "kohm",
                "capacitance": "pF", "length": "um"},
      "paths": [
        {
          "startpoint": "...", "endpoint": "...",
          "path_group": "clk", "path_type": "max",
          "slack": <float>, "arrival": <float>, "required": <float>,
          "driver_resistance": <float|null>, "load_capacitance": <float|null>,
          "segments": [
            {"pin": "_123_/X", "net": "_45_", "layer": "met3",
             "incr_delay": <float>, "wire_length": <float>, "is_wire": true}
          ]
        }
      ]
    }

All numeric fields are in the units declared by the ``units`` block; the parser
converts every value to the engine's SI / femtosecond convention at the
boundary (time → fs, resistance → Ω, capacitance → F, length → m).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

from .core_solver import PathDecision, ProcessParameters, VerticalPathEvaluator

SCHEMA_ID = "logic-folding-baseline/v0"

# ---- Unit conversion tables (declared unit -> engine SI/fs convention) ------

_TIME_TO_FS = {"fs": 1.0, "ps": 1.0e3, "ns": 1.0e6, "us": 1.0e9, "ms": 1.0e12, "s": 1.0e15}
_RES_TO_OHM = {"ohm": 1.0, "kohm": 1.0e3, "Mohm": 1.0e6}
_CAP_TO_F = {"F": 1.0, "mF": 1.0e-3, "uF": 1.0e-6, "nF": 1.0e-9, "pF": 1.0e-12, "fF": 1.0e-15}
_LEN_TO_M = {"m": 1.0, "mm": 1.0e-3, "um": 1.0e-6, "µm": 1.0e-6, "nm": 1.0e-9}


def _factor(table: dict[str, float], unit: str, kind: str) -> float:
    try:
        return table[unit]
    except KeyError:
        raise ValueError(
            f"unsupported {kind} unit {unit!r}; supported: {sorted(table)}"
        ) from None


# ---- Normalised records (SI / femtoseconds) --------------------------------


@dataclass(frozen=True)
class WireSegment:
    """One pin-to-pin delay arc on a timing path, normalised to SI/fs.

    ``is_wire`` distinguishes net (interconnect) delay arcs — the only ones a
    fold can reclaim — from cell (gate) delay arcs, which folding does not
    remove.
    """

    pin: str
    net: Optional[str]
    layer: Optional[str]
    incr_delay_fs: float
    wire_length_m: float
    is_wire: bool


@dataclass(frozen=True)
class BaselinePath:
    """One 2D timing path, normalised to SI/fs.

    Slack/arrival/required keep their sign (a critical path has negative slack).
    ``driver_resistance_ohm`` / ``load_capacitance_farad`` are the path's
    R_drv / C_load if the baseline tool reported them; they are inputs to the
    Eq. 2 *tax*, so carrying them lets a caller build matching
    :class:`ProcessParameters` (see :func:`params_from_path`).
    """

    startpoint: str
    endpoint: str
    slack_fs: float
    arrival_fs: float
    required_fs: float
    segments: tuple[WireSegment, ...]
    path_group: Optional[str] = None
    path_type: Optional[str] = None
    driver_resistance_ohm: Optional[float] = None
    load_capacitance_farad: Optional[float] = None

    @property
    def total_wire_length_m(self) -> float:
        """Sum of horizontal wire length on the path — Eq. 2's ``l_h``."""
        return sum(s.wire_length_m for s in self.segments if s.is_wire)

    @property
    def total_wire_delay_fs(self) -> float:
        """Sum of net (interconnect) delay on the path, in fs.

        This is the *upper bound* on what a fold could reclaim: it counts every
        wire arc. How much of it is actually foldable is a §7 modelling
        decision — see :func:`derive_foldable_savings`.
        """
        return sum(s.incr_delay_fs for s in self.segments if s.is_wire)


@dataclass(frozen=True)
class BaselineReport:
    """A parsed ``logic-folding-baseline/v0`` report: metadata + paths."""

    pdk: Optional[str]
    design: Optional[str]
    corner: Optional[str]
    paths: tuple[BaselinePath, ...]


# ---- Parser (schema v0 dict -> normalised records) -------------------------


def parse_baseline_report(data: dict) -> BaselineReport:
    """Parse a ``logic-folding-baseline/v0`` dict into a :class:`BaselineReport`.

    Converts every numeric field from the declared ``units`` to the engine's
    SI/fs convention. Raises ``ValueError`` on an unknown schema id or unit.
    """
    schema = data.get("schema")
    if schema != SCHEMA_ID:
        raise ValueError(
            f"unexpected schema {schema!r}; this parser handles {SCHEMA_ID!r}"
        )

    units = data.get("units", {})
    t = _factor(_TIME_TO_FS, units.get("time", "ns"), "time")
    r = _factor(_RES_TO_OHM, units.get("resistance", "ohm"), "resistance")
    c = _factor(_CAP_TO_F, units.get("capacitance", "F"), "capacitance")
    ell = _factor(_LEN_TO_M, units.get("length", "m"), "length")

    paths: list[BaselinePath] = []
    for p in data.get("paths", []):
        segments = tuple(
            WireSegment(
                pin=str(seg["pin"]),
                net=(str(seg["net"]) if seg.get("net") is not None else None),
                layer=(str(seg["layer"]) if seg.get("layer") is not None else None),
                incr_delay_fs=float(seg.get("incr_delay", 0.0)) * t,
                wire_length_m=float(seg.get("wire_length", 0.0)) * ell,
                is_wire=bool(seg.get("is_wire", False)),
            )
            for seg in p.get("segments", [])
        )
        drv = p.get("driver_resistance")
        load = p.get("load_capacitance")
        paths.append(
            BaselinePath(
                startpoint=str(p["startpoint"]),
                endpoint=str(p["endpoint"]),
                slack_fs=float(p["slack"]) * t,
                arrival_fs=float(p.get("arrival", 0.0)) * t,
                required_fs=float(p.get("required", 0.0)) * t,
                segments=segments,
                path_group=(str(p["path_group"]) if p.get("path_group") else None),
                path_type=(str(p["path_type"]) if p.get("path_type") else None),
                driver_resistance_ohm=(float(drv) * r if drv is not None else None),
                load_capacitance_farad=(float(load) * c if load is not None else None),
            )
        )
    return BaselineReport(
        pdk=data.get("pdk"),
        design=data.get("design"),
        corner=data.get("corner"),
        paths=tuple(paths),
    )


def load_baseline_report(source: Union[str, Path]) -> BaselineReport:
    """Load and parse a schema-v0 JSON file emitted by ``flows/sta_dump.tcl``."""
    text = Path(source).read_text(encoding="utf-8")
    return parse_baseline_report(json.loads(text))


# ---- Join: 2D baseline -> Eq. 2 --------------------------------------------


def params_from_path(
    path: BaselinePath,
    *,
    r_v: float,
    c_v: float,
    r_b: float,
    c_b: float,
    dtau_red_fs: float,
    dtau_thermal_fs: float,
    parasitic_noise_floor_fs: float = 0.0,
) -> ProcessParameters:
    """Build Eq. 2 :class:`ProcessParameters` from a baseline path.

    R_drv and C_load come from the 2D baseline (the path's driver and load);
    the vertical via/bond parasitics and the redundancy/thermal derates are the
    3D *tax*, supplied by the caller because no 2D tool can measure them.
    """
    if path.driver_resistance_ohm is None or path.load_capacitance_farad is None:
        raise ValueError(
            "path lacks driver_resistance/load_capacitance; "
            "pass an explicit ProcessParameters to screen_path() instead"
        )
    return ProcessParameters(
        r_v=r_v,
        c_v=c_v,
        r_b=r_b,
        c_b=c_b,
        r_drv=path.driver_resistance_ohm,
        c_load=path.load_capacitance_farad,
        dtau_red_fs=dtau_red_fs,
        dtau_thermal_fs=dtau_thermal_fs,
        parasitic_noise_floor_fs=parasitic_noise_floor_fs,
    )


def derive_foldable_savings(path: BaselinePath, threshold_fs: float = 25_000.0) -> float:
    """Δτ_save: horizontal delay (fs) a fold reclaims from ``path`` — memo §7.

    **Policy 2 (long-segment-only).** Sums the interconnect delay of *net* arcs
    whose own delay clears a global-routing criticality ``threshold_fs``
    (default 25 ps). Two arcs contribute nothing by construction:

    * **Cell (gate) arcs** — ``is_wire`` is false. Folding relocates wires, not
      logic; a standard cell's internal delay is untouched by stacking.
    * **Short, local net arcs below the threshold** — assumed to stay on-tier
      (Tier 0/1 local pin connections), reclaiming zero.

    Only the long global / semi-global RC bottlenecks survive, which is the §7
    reading that keeps folding in the *floorplanning* category rather than
    asserting a standard-cell-level scaling law. The vertical via/bond tax then
    competes against this number in Eq. 2.

    The result is in femtoseconds, is ``>= 0``, and never exceeds
    ``path.total_wire_delay_fs`` — it is a subset sum of the path's wire arcs.
    Raising ``threshold_fs`` is more conservative (fewer paths qualify); a
    threshold of ``0.0`` degenerates to the optimistic "all wire delay" policy.
    """
    return sum(
        seg.incr_delay_fs
        for seg in path.segments
        if seg.is_wire and seg.incr_delay_fs >= threshold_fs
    )


def screen_path(
    path: BaselinePath,
    params: ProcessParameters,
    *,
    n_vertical_vias: int,
    n_bond_contacts: int,
    savings_fn: Callable[[BaselinePath], float] = derive_foldable_savings,
) -> PathDecision:
    """Run one 2D baseline path through the Eq. 2 break-even gate.

    The 2D baseline supplies Δτ_save (via ``savings_fn``) and ``l_h``
    (``path.total_wire_length_m``); ``params`` plus the via/bond counts supply
    the 3D tax. Returns the engine's :class:`PathDecision`.
    """
    savings_fs = savings_fn(path)
    evaluator = VerticalPathEvaluator(params)
    return evaluator.evaluate(
        horizontal_savings_fs=savings_fs,
        n_vertical_vias=n_vertical_vias,
        n_bond_contacts=n_bond_contacts,
        l_h_meters=path.total_wire_length_m,
    )
