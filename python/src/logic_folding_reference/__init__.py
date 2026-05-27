"""logic_folding_reference: open-flow stub for LogicFolding break-even screening.

This package implements memo §7 Eq. 2 (path-level break-even) for arbitrary input
parasitics. It is a reference flow per memo §11; it is not a feasibility claim.
"""

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
]
