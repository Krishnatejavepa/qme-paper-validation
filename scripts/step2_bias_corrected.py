#!/usr/bin/env python
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""
step2_bias_corrected.py, Phase B Step 2: bias-corrected held-out MAE.

Reads:  data/q1_oos_results.csv (74 OOS rows)
Writes: data/step2_per_compound.csv
        data/step2_summary.json
(Paths resolve under $QME_ROOT, default = repo root.)

Methodology (locked by preregistration_2026-06-08.md, SHA bd254c2):

  PRIMARY METRIC: held-out MAE on the bias-correction-validation set, computed
  as the upper edge of the 95% bootstrap CI (conservative; worse end of CI is
  the operational verdict number).

  SPLIT: leave-one-family-out CV if any family has >= 10 compounds (preferred);
  else stratified 2-fold; else in-sample (PROVISIONAL). Family counts printed
  BEFORE the split is chosen so the choice is auditable.

  FAILURE MODES (each invalidates the verdict):
    F1 max-min family bias > 0.15 V across families with >= 5 compounds
    F2 a compound's bias was estimated using its own signed error (in-sample)
    F3 held-out set has fewer than 20 compounds (verdict PROVISIONAL)
    F4 sign of bias differs across families with >= 5 compounds

No MP fetch. No DFT. No edits to qme.db. The script is read-only against the
input CSV and writes only to the two output files.
"""
from __future__ import annotations
import csv
import json
import os
import re
from pathlib import Path
from collections import defaultdict
from statistics import mean

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("QME_ROOT", HERE.parent))
DATA = ROOT / "data"
INPUT_CSV = DATA / "q1_oos_results.csv"
OUTPUT_CSV = DATA / "step2_per_compound.csv"
OUTPUT_JSON = DATA / "step2_summary.json"

PREREG_SHA = "bd254c2"     # SHA of preregistration_2026-06-08.md commit
RAW_MAE_EXPECTED = 0.5892
RAW_BIAS_EXPECTED = 0.4263
TOL_SANITY = 0.001         # if reproduced MAE/bias differs by more than this -> data discrepancy
F1_BIAS_SPREAD_THRESHOLD = 0.15
F3_HELDOUT_MIN_N = 20
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42        # deterministic CI
TIERS = [
    ("screening-grade",   lambda v: v < 0.30),
    ("ranking-only",      lambda v: 0.30 <= v <= 0.50),
    ("not screening-grade", lambda v: v > 0.50),
]


# ------------------------------------------------------------------------------
# Family classification (committed alongside the data; this IS the derivation rule)
# ------------------------------------------------------------------------------
# Buckets per pre-registration: {layered_oxide, polyanionic_phosphate,
# polyanionic_sulfate, NASICON, prussian_blue_like, other}.
#
# Rule (first match wins; documented + auditable):
#   R1. formula contains 'CN' substring                          -> prussian_blue_like
#   R2. element set contains F                                   -> other  (fluoride;
#        no fluoride/fluorophosphate bucket in pre-reg list, so they fall into 'other')
#   R3. element set contains any of {C, Si, As}                  -> other  (mixed-anion
#        polyanionics like PCO7/SiCO7/AsCO7 don't fit clean phosphate/sulfate; honest 'other')
#   R4. formula contains '(PO4)3' substring                      -> NASICON  (M2(PO4)3 / Na3M2(PO4)3 family)
#   R5. element set contains P and O and not S                   -> polyanionic_phosphate
#   R6. element set contains S and O and not P                   -> polyanionic_sulfate
#   R7. element set contains S and P                             -> other  (mixed P-S; rare here)
#   R8. element set contains O only (no P/S/F/C/Si/As/CN)        -> layered_oxide
#   R9. otherwise                                                -> other
#
# Notes on the OOS data:
#  - Fluorides (NaXY2MF6 etc.) -> 'other' because the pre-reg bucket list omits a
#    fluoride family; flagging them as 'other' is honest. They show up as a
#    distinct subgroup inside 'other' (see Step 2 report).
#  - PCO7/AsCO7/SiCO7 mixed polyanionics are the bulk of the OOS set and are
#    structurally exotic vs. clean phosphate cathodes; 'other' is correct.

def classify_family(formula: str) -> str:
    # R1: prussian-blue cyanide
    if 'CN' in formula or '(CN)' in formula:
        return 'prussian_blue_like'
    # Element set
    elements = set(re.findall(r'[A-Z][a-z]?', formula))
    # R2-R3: exclusions that send to 'other'
    if 'F' in elements:
        return 'other'   # fluoride
    if elements & {'C', 'Si', 'As'}:
        return 'other'   # mixed-anion polyanionic
    # R4: NASICON pattern (Mo2(PO4)3-like)
    if '(PO4)3' in formula:
        return 'NASICON'
    has_p = 'P' in elements
    has_s = 'S' in elements
    has_o = 'O' in elements
    # R5
    if has_p and has_o and not has_s:
        return 'polyanionic_phosphate'
    # R6
    if has_s and has_o and not has_p:
        return 'polyanionic_sulfate'
    # R7
    if has_s and has_p:
        return 'other'
    # R8
    if has_o and not has_p and not has_s:
        return 'layered_oxide'
    # R9
    return 'other'


# ------------------------------------------------------------------------------
# Load
# ------------------------------------------------------------------------------
def load_rows():
    rows = []
    with open(INPUT_CSV) as fh:
        for r in csv.DictReader(fh):
            if not r['v_pred'] or not r['v_ref_mp']:
                continue
            rows.append({
                'mp_id': r['mp_id'],
                'formula': r['formula'],
                'v_pred': float(r['v_pred']),
                'v_ref': float(r['v_ref_mp']),
                'signed_err': float(r['signed_err']),
                'abs_err': float(r['abs_err']),
                'family': classify_family(r['formula']),
            })
    return rows


# ------------------------------------------------------------------------------
# Metric helpers
# ------------------------------------------------------------------------------
def mae(arr):  return float(np.mean(np.abs(arr)))
def rmse(arr): return float(np.sqrt(np.mean(np.square(arr))))
def bias(arr): return float(np.mean(arr))


def bootstrap_ci(residuals, n_boot=BOOTSTRAP_N, seed=BOOTSTRAP_SEED):
    """Bootstrap 95% CI on MAE of `residuals` (absolute values applied inside)."""
    rng = np.random.default_rng(seed)
    n = len(residuals)
    if n == 0:
        return (None, None, None)
    arr = np.asarray(residuals, dtype=float)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots[i] = float(np.mean(np.abs(arr[idx])))
    return (float(np.percentile(boots, 2.5)),
            float(np.percentile(boots, 50)),
            float(np.percentile(boots, 97.5)))


def tier_of(mae_value):
    for name, pred in TIERS:
        if pred(mae_value):
            return name
    return 'unknown'


# ------------------------------------------------------------------------------
# Main analysis
# ------------------------------------------------------------------------------
def main():
    rows = load_rows()
    n = len(rows)
    print(f"[load] {n} rows from {INPUT_CSV.name}")

    # -- Sanity check: reproduce 0.5892 MAE / +0.4263 bias from the source CSV --
    signed_all = np.array([r['signed_err'] for r in rows])
    raw_mae = mae(signed_all)
    raw_bias = bias(signed_all)
    raw_rmse = rmse(signed_all)
    print(f"\n[sanity] raw MAE  = {raw_mae:.4f}  (expected {RAW_MAE_EXPECTED:.4f}, "
          f"delta {abs(raw_mae - RAW_MAE_EXPECTED):.4f})")
    print(f"[sanity] raw bias = {raw_bias:+.4f}  (expected {RAW_BIAS_EXPECTED:+.4f}, "
          f"delta {abs(raw_bias - RAW_BIAS_EXPECTED):.4f})")
    sanity_pass = (abs(raw_mae - RAW_MAE_EXPECTED) <= TOL_SANITY and
                   abs(raw_bias - RAW_BIAS_EXPECTED) <= TOL_SANITY)
    print(f"[sanity] PASS" if sanity_pass else "[sanity] FAIL, STOP and reconcile data")
    if not sanity_pass:
        raise SystemExit(1)

    # -- Family classification, committed rule above --
    families = defaultdict(list)
    for r in rows:
        families[r['family']].append(r)
    family_counts = {fam: len(items) for fam, items in families.items()}
    family_counts_sorted = dict(sorted(family_counts.items(), key=lambda kv: -kv[1]))
    print(f"\n[families] counts (rule embedded in classify_family() above):")
    for fam, c in family_counts_sorted.items():
        print(f"           {fam:30s} {c}")

    # -- Choose split method per pre-reg --
    ge10 = [fam for fam, c in family_counts.items() if c >= 10]
    if ge10:
        split_method = 'leave_one_family_out'
        split_note = (f"LOFO across families with >=10 compounds: {sorted(ge10)}. "
                      f"For each, hold the family out, learn the global mean signed error "
                      f"on the remaining compounds, apply it to the held-out family.")
    else:
        # Fallback (2): stratified 2-fold
        # Hard fallback (3) only if (2) infeasible, which it is here as long as we have
        # multiple compounds per family.
        split_method = 'stratified_2fold'
        split_note = ("No family has >=10 compounds; using stratified 2-fold by family, "
                      f"seed={BOOTSTRAP_SEED}.")
    print(f"\n[split] {split_method} ,  {split_note}")

    # -- Apply split --
    if split_method == 'leave_one_family_out':
        heldout_rows = []           # (row, bias_used, residual_signed_err)
        f2_violations = 0           # F2 should be 0 by construction
        for fam in ge10:
            train_signed = np.array([r['signed_err'] for r in rows
                                     if r['family'] != fam])
            bias_on_train = float(np.mean(train_signed))
            for r in families[fam]:
                # Make sure this compound's own signed_err is NOT in the training pool
                # (which it isn't, because it's in family fam which is held out)
                if r in [x for x in rows if x['family'] != fam]:
                    f2_violations += 1
                resid = r['signed_err'] - bias_on_train
                heldout_rows.append((r, bias_on_train, resid))
        # Other families (size < 10) contribute as training-only to each fold; they have
        # no held-out evaluation. We mark them so the per-compound CSV is complete.
        nonheld = [r for r in rows if r['family'] not in ge10]
    else:
        # Stratified 2-fold by family
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        fold_a, fold_b = [], []
        for fam, items in families.items():
            shuffled = items[:]
            rng.shuffle(shuffled)
            mid = len(shuffled) // 2
            fold_a.extend(shuffled[:mid])
            fold_b.extend(shuffled[mid:])
        heldout_rows = []
        f2_violations = 0
        for held, fit in [(fold_a, fold_b), (fold_b, fold_a)]:
            fit_signed = np.array([r['signed_err'] for r in fit])
            bias_on_fit = float(np.mean(fit_signed))
            for r in held:
                if r in fit:
                    f2_violations += 1
                resid = r['signed_err'] - bias_on_fit
                heldout_rows.append((r, bias_on_fit, resid))
        nonheld = []

    held_n = len(heldout_rows)
    print(f"\n[heldout] N held-out = {held_n}")

    # -- F2 check --
    f2_status = 'PASS' if f2_violations == 0 else f'FAIL ({f2_violations} violations)'
    print(f"[F2] in-sample contamination: {f2_status}")

    # -- F3 check --
    f3_fired = held_n < F3_HELDOUT_MIN_N
    f3_status = 'PASS' if not f3_fired else f'FAIL (N={held_n} < {F3_HELDOUT_MIN_N}) -> PROVISIONAL'
    print(f"[F3] held-out size:    {f3_status}")

    # -- Per-family bias (independent of split, on full 74, diagnostic) --
    per_family = {}
    for fam, items in families.items():
        sgn = np.array([r['signed_err'] for r in items])
        per_family[fam] = {
            'n': len(items),
            'bias': float(np.mean(sgn)),
            'mae': float(np.mean(np.abs(sgn))),
            'sign': '+' if float(np.mean(sgn)) > 0 else ('-' if float(np.mean(sgn)) < 0 else '0'),
        }
    print(f"\n[per-family] (all 74, diagnostic; >=5 compounds counted for F1/F4)")
    for fam, info in sorted(per_family.items(), key=lambda kv: -kv[1]['n']):
        print(f"   {fam:30s} n={info['n']:3d}  bias={info['bias']:+.4f} V  mae={info['mae']:.4f} V")

    fams_ge5 = {fam: info for fam, info in per_family.items() if info['n'] >= 5}
    biases_ge5 = [info['bias'] for info in fams_ge5.values()]
    if biases_ge5:
        bias_spread = max(biases_ge5) - min(biases_ge5)
    else:
        bias_spread = 0.0
    f1_fired = bias_spread > F1_BIAS_SPREAD_THRESHOLD
    f1_status = (f'PASS (spread {bias_spread:.4f} <= {F1_BIAS_SPREAD_THRESHOLD})' if not f1_fired
                 else f'FAIL (spread {bias_spread:.4f} > {F1_BIAS_SPREAD_THRESHOLD})')
    print(f"\n[F1] family-bias spread (>=5 compounds): {f1_status}")
    signs = {info['sign'] for info in fams_ge5.values() if info['sign'] != '0'}
    f4_fired = ('+' in signs and '-' in signs)
    f4_status = 'PASS (all same sign)' if not f4_fired else f'FAIL (mixed signs {signs})'
    print(f"[F4] family-bias signs (>=5 compounds):  {f4_status}")

    # -- Primary metric: bias-corrected held-out MAE, with bootstrap CI --
    held_residuals = np.array([resid for (_, _, resid) in heldout_rows])
    held_mae_point = mae(held_residuals)
    held_rmse_point = rmse(held_residuals)
    held_bias_point = bias(held_residuals)
    ci_low, ci_med, ci_high = bootstrap_ci(held_residuals)
    print(f"\n[primary] held-out residuals: n={held_n}")
    print(f"          bias-corrected MAE point estimate = {held_mae_point:.4f} V")
    print(f"          RMSE (residuals)                  = {held_rmse_point:.4f} V")
    print(f"          residual bias                     = {held_bias_point:+.4f} V (should be ~0)")
    print(f"          bootstrap 95% CI                  = ({ci_low:.4f}, {ci_med:.4f}, {ci_high:.4f}) V")
    print(f"          <- upper edge {ci_high:.4f} V is the PRIMARY (conservative) metric")

    # -- Tier verdict --
    primary = ci_high   # conservative: upper edge of CI
    tier = tier_of(primary)
    print(f"\n[tier] conservative primary metric = {primary:.4f} V -> tier '{tier}'")

    # -- Compose verdict considering failure modes --
    fired = [name for (name, fired_) in
             (('F1', f1_fired), ('F2', f2_violations > 0),
              ('F3', f3_fired), ('F4', f4_fired))
             if fired_]
    if fired:
        verdict_str = f"INVALIDATED by failure mode(s): {', '.join(fired)} (see below)"
    else:
        verdict_str = f"tier = {tier} (primary = {primary:.4f} V conservative)"
    print(f"\n[VERDICT] {verdict_str}")

    # -- Per-compound CSV --
    with open(OUTPUT_CSV, 'w', newline='') as fh:
        cols = ['mp_id', 'formula', 'family', 'v_pred', 'v_ref', 'signed_err',
                'bias_used_for_correction', 'v_pred_corrected', 'residual_signed_error',
                'in_heldout_set']
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        held_lookup = {id(r): (b, resid) for (r, b, resid) in heldout_rows}
        for r in rows:
            if id(r) in held_lookup:
                b_used, resid = held_lookup[id(r)]
                w.writerow({
                    **{k: r[k] for k in ['mp_id', 'formula', 'family', 'v_pred', 'v_ref', 'signed_err']},
                    'bias_used_for_correction': round(b_used, 6),
                    'v_pred_corrected': round(r['v_pred'] - b_used, 6),
                    'residual_signed_error': round(resid, 6),
                    'in_heldout_set': True,
                })
            else:
                # nonheld: family <10 in LOFO mode. Not in any held-out fold.
                w.writerow({
                    **{k: r[k] for k in ['mp_id', 'formula', 'family', 'v_pred', 'v_ref', 'signed_err']},
                    'bias_used_for_correction': '',
                    'v_pred_corrected': '',
                    'residual_signed_error': '',
                    'in_heldout_set': False,
                })
    print(f"\n[wrote] {OUTPUT_CSV.name} ({len(rows)} rows total; {held_n} held-out)")

    # -- Summary JSON --
    summary = {
        'preregistration_commit_sha_short': PREREG_SHA,
        'n_total_oos': n,
        'sanity_check': {
            'raw_mae_reproduced': round(raw_mae, 4),
            'raw_mae_expected': RAW_MAE_EXPECTED,
            'raw_bias_reproduced': round(raw_bias, 4),
            'raw_bias_expected': RAW_BIAS_EXPECTED,
            'raw_rmse': round(raw_rmse, 4),
            'pass': sanity_pass,
        },
        'family_counts': family_counts_sorted,
        'split_method': split_method,
        'split_note': split_note,
        'heldout_n': held_n,
        'failure_modes': {
            'F1_family_bias_spread_threshold_V': F1_BIAS_SPREAD_THRESHOLD,
            'F1_observed_spread_V': round(bias_spread, 4),
            'F1_fired': f1_fired,
            'F2_in_sample_violations': f2_violations,
            'F2_fired': f2_violations > 0,
            'F3_heldout_min_n': F3_HELDOUT_MIN_N,
            'F3_observed_heldout_n': held_n,
            'F3_fired': f3_fired,
            'F4_mixed_sign_families': sorted(signs),
            'F4_fired': f4_fired,
            'any_fired': bool(fired),
            'fired_list': fired,
        },
        'per_family_diagnostic': per_family,
        'primary_metric': {
            'definition': 'held-out MAE upper edge of 95% bootstrap CI (conservative)',
            'value_V': round(primary, 4),
            'point_estimate_V': round(held_mae_point, 4),
            'ci95_lo_V': round(ci_low, 4),
            'ci95_med_V': round(ci_med, 4),
            'ci95_hi_V': round(ci_high, 4),
            'rmse_V': round(held_rmse_point, 4),
            'residual_bias_V': round(held_bias_point, 4),
            'bootstrap_n': BOOTSTRAP_N,
            'bootstrap_seed': BOOTSTRAP_SEED,
        },
        'tier_at_primary_metric': tier,
        'verdict_string': verdict_str,
        'caveat': ("Reference voltages are MP `average_voltage`, DFT-computed (PBE/PBE+U), "
                   "NOT experimental. Step 3 will replace with literature-experimental V_avg "
                   "on the 28 mainstream subset, which may shift the verdict by up to ~0.15 V "
                   "per F3 / revision-trigger criteria in the pre-registration."),
        'na3v2po43_note': ("Na3V2(PO4)3 is NOT in the OOS set. The audit's '2.90 V vs ~3.4 V exp' "
                          "is a separate QME PBE+U DFT result and is out of scope here."),
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"[wrote] {OUTPUT_JSON.name}")

    # -- Compact final line for piping --
    print()
    print("=" * 78)
    print(f"FINAL: split={split_method} held_n={held_n} primary_MAE={primary:.4f}V "
          f"tier='{tier}' fired={fired or 'none'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
