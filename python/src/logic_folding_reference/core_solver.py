"""Path-level break-even screening engine for 3D vertical logic folding.

This module implements the path-level break-even inequality from §7, Eq. 2 of
the LogicFolding No-Action Decision Memo (v4, 2026-05-27):

    Δτ_save(l_h) > N_v · (R_v·C_load + R_drv·C_v + R_v·C_v)
                 + N_b · (R_b·C_load + R_drv·C_b + R_b·C_b)
                 + Δτ_red
                 + Δτ_T

The left-hand side is horizontal-wire delay reclaimed by folding a segment of
effective length ``l_h`` into the vertical dimension. The right-hand side is
the parasitic, redundancy, and thermal-derating tax that vertical folding
introduces.

Each parenthetical group on the right is the standard Elmore-style delay
contribution of one inter-tier transition:

* ``R_x · C_load`` — driver of the vertical contact sees the load downstream;
* ``R_drv · C_x``  — driver of the vertical contact must charge the contact's
  own capacitance;
* ``R_x · C_x``    — the contact's self-loading (half-Elmore quadratic term).

The third self-loading term is the one the memo's red-team reviewers flagged
as load-bearing once parasitics are measured rather than assumed; it is
included here verbatim so the gate is not artificially loosened.

All time quantities are in **femtoseconds (fs)**, resistances in **ohms**,
capacitances in **farads**. The convention follows OpenROAD / OpenSTA outputs.

Per memo §7: "The gate is not 'achieve X fF-ohm.' The gate is: For the actual
folded paths, under measured parasitics and temperature derates, Eq. 2 must
hold for enough critical paths to improve sustained system performance per
watt after area, yield, and cost penalties."

This module evaluates the inequality for one path at a time and returns the
exact margin. It does *not* aggregate across paths into a portability claim;
that is intentionally outside scope per memo §11.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


# ---- Unit conventions ------------------------------------------------------

# RC product in (ohm · farad) = seconds. Memo Eq. 2 is dimensionally in time.
# We convert to femtoseconds at the boundary to keep arithmetic clean.
SECONDS_TO_FS = 1.0e15


class DecisionLabel(str, Enum):
    """Three-way label for one path's break-even result.

    ``PASS``     — horizontal savings strictly exceed the vertical tax by a
                   margin larger than the measurement noise floor.
    ``FAIL``     — vertical tax dominates; folding this path costs delay.
    ``MARGINAL`` — algebraic margin is within the noise floor of the supplied
                   parasitic measurements. Memo §7 implies that uncalibrated
                   wins are not wins; callers should treat this as advisory
                   only.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    MARGINAL = "MARGINAL"


@dataclass(frozen=True)
class ProcessParameters:
    """Measured or extracted physical primitives for one folded path.

    Fields map 1:1 to memo §7 symbols. No default values — the memo's explicit
    position is that arbitrary targets are not credible, so callers must supply
    numbers from extraction or measurement.
    """

    r_v: float
    c_v: float
    r_b: float
    c_b: float
    r_drv: float
    c_load: float
    dtau_red_fs: float
    dtau_thermal_fs: float
    parasitic_noise_floor_fs: float = 0.0

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if value < 0:
                raise ValueError(
                    f"{name}={value!r} is negative; "
                    f"physical primitives must be non-negative."
                )


@dataclass(frozen=True)
class PathDecision:
    """Result of evaluating Eq. 2 for one folded path."""

    margin_fs: float
    horizontal_savings_fs: float
    vertical_tax_fs: float
    n_vertical_vias: int
    n_bond_contacts: int
    l_h_meters: float
    label: Optional[DecisionLabel] = None


class VerticalPathEvaluator:
    """Evaluator for the LogicFolding path-level break-even inequality.

    One evaluator instance binds one set of ``ProcessParameters`` and can be
    called many times across different paths.
    """

    def __init__(self, params: ProcessParameters) -> None:
        self._p = params

    @property
    def params(self) -> ProcessParameters:
        return self._p

    # -- Internal: the vertical-tax sum (RHS of Eq. 2) -----------------------

    def _via_contribution_fs(self) -> float:
        """Single vertical via's full Elmore contribution in fs.

        Equation: ``R_v·C_load + R_drv·C_v + R_v·C_v``.
        """
        p = self._p
        rc_seconds = (
            p.r_v * p.c_load        # via drives downstream load
            + p.r_drv * p.c_v       # driver charges via cap
            + p.r_v * p.c_v         # via's own self-loading (half-Elmore)
        )
        return rc_seconds * SECONDS_TO_FS

    def _bond_contribution_fs(self) -> float:
        """Single F2F bond contact's full Elmore contribution in fs.

        Equation: ``R_b·C_load + R_drv·C_b + R_b·C_b``.
        """
        p = self._p
        rc_seconds = (
            p.r_b * p.c_load
            + p.r_drv * p.c_b
            + p.r_b * p.c_b
        )
        return rc_seconds * SECONDS_TO_FS

    def vertical_tax_fs(self, n_vertical_vias: int, n_bond_contacts: int) -> float:
        """Right-hand side of memo Eq. 2 in femtoseconds.

        ``N_v · via_term + N_b · bond_term + Δτ_red + Δτ_T``.
        """
        if n_vertical_vias < 0 or n_bond_contacts < 0:
            raise ValueError("Contact counts must be non-negative.")
        return (
            n_vertical_vias * self._via_contribution_fs()
            + n_bond_contacts * self._bond_contribution_fs()
            + self._p.dtau_red_fs
            + self._p.dtau_thermal_fs
        )

    # -- Public: one-path evaluation ----------------------------------------

    def evaluate(
        self,
        horizontal_savings_fs: float,
        n_vertical_vias: int,
        n_bond_contacts: int,
        l_h_meters: float,
    ) -> PathDecision:
        """Evaluate Eq. 2 for one path. Returns label + margin."""
        if horizontal_savings_fs < 0:
            raise ValueError("horizontal_savings_fs cannot be negative.")
        if l_h_meters < 0:
            raise ValueError("l_h_meters cannot be negative.")

        tax_fs = self.vertical_tax_fs(n_vertical_vias, n_bond_contacts)
        margin_fs = horizontal_savings_fs - tax_fs
        label = self._classify_decision(margin_fs)

        return PathDecision(
            label=label,
            margin_fs=margin_fs,
            horizontal_savings_fs=horizontal_savings_fs,
            vertical_tax_fs=tax_fs,
            n_vertical_vias=n_vertical_vias,
            n_bond_contacts=n_bond_contacts,
            l_h_meters=l_h_meters,
        )

    # Backwards-compatible alias matching the user's task-spec method name.
    calculate_path_slack_delta = evaluate

    def _classify_decision(self, margin_fs: float) -> DecisionLabel:
        """Map a signed margin (fs) to a PASS / FAIL / MARGINAL label.

        Policy choice: three-way classification with a measurement-noise band.
        This is the most defensible reading of memo §7 and §8.1: a path only
        passes when its positive break-even margin is outside the supplied
        parasitic calibration floor. Values inside a nonzero noise floor are
        labeled MARGINAL, including small negative values, because the measured
        sign is not trustworthy enough to support adoption or rejection.
        """
        noise_floor = self._p.parasitic_noise_floor_fs
        if noise_floor > 0.0 and abs(margin_fs) <= noise_floor:
            return DecisionLabel.MARGINAL
        if margin_fs > 0.0:
            return DecisionLabel.PASS
        return DecisionLabel.FAIL

    # -- Public: batch evaluation -------------------------------------------

    def evaluate_batch(
        self,
        paths: Iterable[tuple[float, int, int, float]],
    ) -> list[PathDecision]:
        """Evaluate Eq. 2 across many paths.

        Each item in ``paths`` is a ``(horizontal_savings_fs, n_vertical_vias,
        n_bond_contacts, l_h_meters)`` tuple. Returned list preserves order.
        """
        return [self.evaluate(*p) for p in paths]
