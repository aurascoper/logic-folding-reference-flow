//! `logic_folding_core` — vectorised LogicFolding break-even evaluator.
//!
//! Implements the path-level break-even inequality from §7 of the LogicFolding
//! No-Action Decision Memo (v4, 2026-05-27).
//!
//! The exact form encoded here matches the user's Rust task spec, which is
//! the **abbreviated** form of the memo's Eq. 2:
//!
//! ```text
//! Δτ_save > N_v · (R_v·C_load + R_drv·C_v)
//!         + N_b · (R_b·C_load + R_drv·C_b)
//!         + Δτ_red + Δτ_T
//! ```
//!
//! That is, the via and bond self-loading half-Elmore terms (`R_v·C_v`,
//! `R_b·C_b`) are **omitted** here. The Python solver
//! (`logic_folding_reference::core_solver`) keeps the full form. The two
//! engines therefore answer *slightly different* questions:
//!
//! * The Rust engine is faster, suitable for sweeping millions of mock paths,
//!   and intentionally optimistic about per-via tax.
//! * The Python engine is slower, included for orchestrator-side per-path
//!   reporting, and matches the memo's stated equation verbatim.
//!
//! See `docs/MEMO_INDEX.md` in the repository root for the cross-reference.
//!
//! All time quantities are 64-bit floats in **femtoseconds**. R · C products
//! are evaluated in SI (Ω · F = s) then converted at the boundary.
//!
//! Per memo §11 this crate exists to make the methodology *coherent*, not to
//! claim feasibility. A million mock paths passing the gate does not imply
//! that any silicon does.

use rayon::prelude::*;

pub mod mock;

/// Conversion factor from SI seconds to femtoseconds.
pub const SECONDS_TO_FS: f64 = 1.0e15;

/// Three-way label for one path's break-even result.
#[derive(Debug, Copy, Clone, PartialEq, Eq, Hash)]
pub enum DecisionLabel {
    /// Margin strictly positive and outside the noise floor.
    Pass,
    /// Margin negative or below the noise floor.
    Fail,
    /// |Margin| within the noise floor of the supplied parasitics.
    Marginal,
}

/// Physical primitives for one technology stack. Fields map 1:1 to memo §7.
///
/// `Copy` so the rayon closures can pull a private copy without `Arc`.
#[derive(Debug, Clone, Copy)]
pub struct ProcessParameters {
    /// Resistance of a single vertical inter-tier via (Ω).
    pub r_v: f64,
    /// Capacitance of a single vertical inter-tier via (F).
    pub c_v: f64,
    /// Resistance of a single F2F wafer-bond contact (Ω).
    pub r_b: f64,
    /// Capacitance of a single F2F wafer-bond contact (F).
    pub c_b: f64,
    /// Driver output resistance (Ω).
    pub r_drv: f64,
    /// Downstream load capacitance past the vertical contact (F).
    pub c_load: f64,
    /// Redundancy / test / alignment overhead (fs).
    pub dtau_red_fs: f64,
    /// Thermal-derating delay penalty (fs).
    pub dtau_thermal_fs: f64,
    /// One-sigma noise floor on RHS (fs). Used to classify Marginal vs Pass.
    pub parasitic_noise_floor_fs: f64,
}

impl ProcessParameters {
    /// Per-via Elmore contribution in fs **without** self-loading
    /// (R_v · C_load + R_drv · C_v).
    #[inline]
    fn via_term_fs(&self) -> f64 {
        (self.r_v * self.c_load + self.r_drv * self.c_v) * SECONDS_TO_FS
    }

    /// Per-bond Elmore contribution in fs **without** self-loading
    /// (R_b · C_load + R_drv · C_b).
    #[inline]
    fn bond_term_fs(&self) -> f64 {
        (self.r_b * self.c_load + self.r_drv * self.c_b) * SECONDS_TO_FS
    }
}

/// Geometric quantities that vary per path.
#[derive(Debug, Clone, Copy)]
pub struct PathInput {
    /// Δτ_save (fs).
    pub horizontal_savings_fs: f64,
    /// N_v.
    pub n_vertical_vias: u32,
    /// N_b.
    pub n_bond_contacts: u32,
}

/// Result of evaluating one path.
#[derive(Debug, Clone, Copy)]
pub struct PathResult {
    pub label: DecisionLabel,
    pub margin_fs: f64,
    pub horizontal_savings_fs: f64,
    pub vertical_tax_fs: f64,
}

/// Thread-safe vectorised evaluator. One instance binds one technology;
/// evaluate many paths against it in parallel.
#[derive(Debug, Clone, Copy)]
pub struct PathEvaluator {
    params: ProcessParameters,
    via_term_fs_cached: f64,
    bond_term_fs_cached: f64,
}

impl PathEvaluator {
    pub fn new(params: ProcessParameters) -> Self {
        let via_term_fs_cached = params.via_term_fs();
        let bond_term_fs_cached = params.bond_term_fs();
        Self {
            params,
            via_term_fs_cached,
            bond_term_fs_cached,
        }
    }

    pub fn params(&self) -> ProcessParameters {
        self.params
    }

    /// Compute Eq. 2 RHS in fs for one path (abbreviated form — see crate doc).
    #[inline]
    pub fn vertical_tax_fs(&self, n_v: u32, n_b: u32) -> f64 {
        (n_v as f64) * self.via_term_fs_cached
            + (n_b as f64) * self.bond_term_fs_cached
            + self.params.dtau_red_fs
            + self.params.dtau_thermal_fs
    }

    /// Evaluate one path.
    #[inline]
    pub fn evaluate(&self, path: &PathInput) -> PathResult {
        let tax = self.vertical_tax_fs(path.n_vertical_vias, path.n_bond_contacts);
        let margin = path.horizontal_savings_fs - tax;
        let noise = self.params.parasitic_noise_floor_fs;
        let label = if noise > 0.0 && margin.abs() <= noise {
            DecisionLabel::Marginal
        } else if margin > 0.0 {
            DecisionLabel::Pass
        } else {
            DecisionLabel::Fail
        };
        PathResult {
            label,
            margin_fs: margin,
            horizontal_savings_fs: path.horizontal_savings_fs,
            vertical_tax_fs: tax,
        }
    }

    /// Evaluate a slice of paths in parallel via rayon. Order preserved.
    pub fn evaluate_parallel(&self, paths: &[PathInput]) -> Vec<PathResult> {
        paths.par_iter().map(|p| self.evaluate(p)).collect()
    }

    /// Convenience: count of (Pass, Fail, Marginal) across paths in parallel.
    pub fn tally_parallel(&self, paths: &[PathInput]) -> (u64, u64, u64) {
        paths
            .par_iter()
            .map(|p| {
                let r = self.evaluate(p);
                match r.label {
                    DecisionLabel::Pass => (1u64, 0u64, 0u64),
                    DecisionLabel::Fail => (0, 1, 0),
                    DecisionLabel::Marginal => (0, 0, 1),
                }
            })
            .reduce(
                || (0u64, 0u64, 0u64),
                |a, b| (a.0 + b.0, a.1 + b.1, a.2 + b.2),
            )
    }
}
