# Phase B Step 2, pre-registration (write-once)

> **This document is committed BEFORE the bias-corrected metric in Step 2 is
> computed. The commit SHA is the audit trail proving the thresholds existed
> before the result. If any problem with this pre-registration is discovered
> during Step 2, the work HALTS and the operator is asked, this document is
> not silently edited.**

Scope: P1 = "can the QMEv2.5 battery Siamese GNN predict Na-ion voltages
well enough to drive screening decisions on the Na-ion pipeline?" Substrate
= the 74 out-of-sample (OOS) Na cathodes from
`na_wedge_diag/q1_oos_results.csv` (held-out by training-set membership: their
sodiated mp-id is NOT among the 20 in `battery_graphs/na_mp-*_Na.pt`).
Reference voltages = MP `average_voltage` (DFT-computed, **not** experimental
- this is labelled honestly throughout and replaced with literature values on
a 28-compound subset in Step 3, not here).

---

## Verdict tiers (verbatim)

| Tier | Range | Operational meaning |
|---|---|---|
| **screening-grade** | held-out MAE **< 0.30 V** | voltage can drive discovery decisions (rank-AND-flag) on the Na pipeline |
| **ranking-only** | **0.30 V ≤ held-out MAE ≤ 0.50 V** | rank within a chemistry family; do NOT trust absolute V for cross-family screening |
| **not screening-grade** | held-out MAE **> 0.50 V** | do not build Na pipeline on it; either fine-tune on Na DFT data or restrict to relative comparisons within one family |

## Primary metric (this is what gets compared to the tiers)

**Held-out MAE on the bias-correction-validation set**, where "held-out" is
defined as compounds whose signed errors did NOT contribute to the bias estimate
applied to them. The split mechanism is specified in Step 2 §S2.2 (priority:
leave-one-family-out CV with ≥10-compound families; fallback: stratified
2-fold; hard fallback: in-sample with PROVISIONAL verdict).

The primary metric is reported as a **conservative lower bound**, specifically
the **upper edge of the 95% bootstrap confidence interval** on the held-out MAE,
not the point estimate. (For MAE a higher number is worse; "conservative" means
"use the worse end of the CI to choose a tier.")

It is **NOT** any of: (a) all-compound MAE on the full 74 (in-sample by
construction); (b) in-sample bias-corrected MAE (learning and applying on the
same compounds); (c) per-family best-case MAE chosen post-hoc.

## Secondary metrics (reported alongside, NOT used to choose a tier)

- RMSE on the held-out set
- Bias (mean signed error) on the held-out set; should be ≈0 by construction
  after correction, non-zero residual bias is a methodology red flag
- Per-family MAE breakdown
- Pre-correction (raw) MAE / RMSE / bias for comparison
- Within-tolerance fractions (±0.2, ±0.3, ±0.5 V) pre- and post-correction
- Bootstrap CI bounds on the primary metric

## Pre-registered failure modes, each INVALIDATES the verdict

**F1. Family-dependent bias.** If per-family bias estimates differ by more than
**0.15 V** (i.e. max(family_bias) − min(family_bias) > 0.15 V across families
with ≥5 compounds), a single global additive bias correction does not
generalize. **Consequence:** verdict downgrades to "calibration is
family-specific; treat as ranking-only at best, scoped to the families where
the correction holds." A clean tier verdict is not issued.

**F2. Held-out validation set contains compounds also used to fit the bias.**
If at any point the bias applied to a compound was estimated using that
compound's own signed error, the analysis is in-sample by construction.
**Consequence:** verdict is "in-sample, re-run with a cleaner split before
issuing a tier." The numbers are still reported but explicitly labelled
in-sample.

**F3. Held-out set has fewer than 20 compounds.** **Consequence:** report MAE
but mark the verdict as **PROVISIONAL**. A held-out N<20 cannot statistically
distinguish neighbouring tiers (≈0.30 vs ≈0.50 V) with confidence.

**F4. Sign of bias differs across families.** If some families have positive
bias and others have negative bias (across families with ≥5 compounds), no
single additive correction is physically meaningful. **Consequence:** verdict
is **RED, pipeline blocked pending model retrain or family-specific
calibration**; no tier is issued.

## Starting numbers (the prior; visible BEFORE thresholds were set)

These were known from the Phase B PRE-AUDIT before this pre-registration was
drafted. The thresholds above were set knowing where the bias-corrected number
might land, this is honest pre-registration of the *verdict mapping*, not of
the result.

- **Raw (in-sample, full-74) MAE:** **0.5892 V** (source:
  `na_wedge_diag/q1_oos_summary.json`)
- **Mean signed error (bias):** **+0.4263 V** (same source; ≈ 72% of the raw
  MAE)
- **Theoretical floor on bias-corrected MAE (lower bound from a single global
  correction):** **|0.5892 − 0.4263| = 0.16 V**. Achievable only if all
  residual error were purely scatter and the bias estimate generalized
  perfectly across the held-out split, which the held-out methodology will
  test, not assume.
- **Most-likely landing zone** post-correction, given some realistic
  family-bias variance and held-out generalization gap: **0.20-0.35 V**, which
  spans both `screening-grade` and `ranking-only`. Either is a GO-state for
  the Na pipeline at different rigor levels. A landing >0.40 V despite the
  +0.43 V bias would indicate that the bias correction does NOT generalize
  cross-family and would likely trigger F1 or F4.

## What would change my mind (revision triggers, post-publication)

The tier verdict issued by Step 2 (whatever it is) is revised if, within
**90 days** of publishing it, any of the following lands:

- An experimentally-measured Na-cathode average voltage in the
  Fe-Mn-P-O-Na box (the in-box chemistry we claim screening over) where the
  QMEv2.5 predicted V_avg, applied with the bias correction issued in
  Step 2, disagrees with experiment by **more than 0.4 V**. A single such
  case downgrades the verdict by one tier; two such cases retire the
  bias-corrected predictor entirely.
- A held-out experimental V_avg curated in Step 3 (28-compound mainstream
  subset) where the bias-corrected MAE on the experimental subset differs
  from the MP-computed subset's MAE by more than 0.15 V, meaning the
  MP-computed reference was a misleading proxy and the Step 2 verdict was
  driven by a substitution artefact.
- Discovery that the 74-compound OOS set has data leakage into the GNN
  training corpus that was not caught by the mp-id training-set membership
  test (e.g. the same compound at a different stoichiometry contributed
  graphs).

Any of these → Step 2 verdict is withdrawn and re-run with corrected data /
methodology, with a new pre-registration.

---

*Drafted before Step 2 metric computation. Audit trail = the commit SHA of
this file.*
