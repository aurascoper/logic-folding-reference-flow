"""logic_folding_reference: open-flow stub for LogicFolding break-even screening.

This package implements memo §7 Eq. 2 (path-level break-even) for arbitrary input
parasitics. It is a reference flow per memo §11; it is not a feasibility claim.

:mod:`logic_folding_reference.baseline` adds the 2D-baseline ingestion contract
(schema ``logic-folding-baseline/v0``) that carries OpenROAD / OpenSTA output
into the Eq. 2 engine.
"""

from .baseline import (
    SCHEMA_ID,
    BaselinePath,
    BaselineReport,
    WireSegment,
    derive_foldable_savings,
    load_baseline_report,
    params_from_path,
    parse_baseline_report,
    screen_path,
)
from .core_solver import (
    DecisionLabel,
    PathDecision,
    ProcessParameters,
    VerticalPathEvaluator,
)

__all__ = [
    "DecisionLabel",
    "PathDecision",
    "ProcessParameters",
    "VerticalPathEvaluator",
    # 2D-baseline ingestion (schema logic-folding-baseline/v0)
    "SCHEMA_ID",
    "BaselinePath",
    "BaselineReport",
    "WireSegment",
    "parse_baseline_report",
    "load_baseline_report",
    "params_from_path",
    "derive_foldable_savings",
    "screen_path",
]
