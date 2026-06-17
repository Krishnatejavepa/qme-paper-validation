#!/usr/bin/env python
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""
PROVENANCE SCRIPT, NOT part of the clean-room reproduce set.
Requires external resources NOT shipped in this repo: a Materials Project API
key (MP_API_KEY), the trained GNN weights (QME_BATTERY_WEIGHTS), the full QME
engine `src/` package, and the live qme.db. It GENERATED the committed outputs
data/s3b_litexp_summary.json and data/s3b_litexp_results.csv. Every headline
number and figure in the paper regenerates from those committed outputs via the
reproducible set (make_tables.py, fig1/2/3, consistency_check.py); this script
is included only for transparency of how those outputs were produced.

s3b_litexp.py, Step 3b: GNN predictions vs MACHINE-CURATED literature V_avg.

Reads na_wedge_diag/curated_na_cathodes.csv (machine-curated, pending operator
spot-check), fetches the MP structure for every row with an mp_id, runs the SAME
inference path as q1_oos.py (predict_from_structure -> Siamese QME_V2_multihead,
active qme-v2.5-battery pinned via QME_BATTERY_WEIGHTS), and computes the
pre-registered metrics against literature V_avg:

  - held-out (all rows are in_training_corpus=False) signed error, MAE, RMSE
  - 95% bootstrap CI on held-out MAE (10k resamples)
  - LOOCV-bias-corrected held-out MAE (pre-reg primary for 5 <= n < 10) + CI
  - all of the above with and without the Tier C row(s)
  - polyanionic_phosphate subset + per-compound residual table
  - three-way decomposition on the Step-2 overlap rows (V_pred-V_MP, V_MP-V_lit,
    V_pred-V_lit)
  - voltage-dependence of residuals (Pearson r of signed error vs V_lit)
  - reproducibility check: mp-562796 / mp-683773 must reproduce the q1_oos
    predictions (3.727 / 3.9209 V) through this run

SAFETY: refuses to run without a throwaway QME_DB_PATH; qme.db untouched.
"""
from __future__ import annotations
import csv, json, os, sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

_dbp = os.environ.get("QME_DB_PATH", "")
if not _dbp or Path(_dbp).resolve().name == "qme.db":
    sys.exit("REFUSING TO RUN: set QME_DB_PATH to a throwaway path (never qme.db).")
KEY = os.environ.get("MP_API_KEY", "")
if not KEY:
    sys.exit("MP_API_KEY not in env.")
if not os.environ.get("QME_BATTERY_WEIGHTS"):
    sys.exit("QME_BATTERY_WEIGHTS not set, pin the active model explicitly (q1_oos parity).")

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
import numpy as np  # noqa: E402

RNG = np.random.default_rng(20260609)
N_BOOT = 10000

# Step-2 overlap rows: MP battery-doc average_voltage (na_ion_candidates.csv)
V_MP = {"mp-562796": 3.961, "mp-683773": 3.7625}
# q1_oos predictions these two rows must reproduce
V_PRED_PRIOR = {"mp-562796": 3.727, "mp-683773": 3.9209}

rows = []
with open(HERE / "curated_na_cathodes.csv") as f:
    rdr = csv.DictReader(r for r in f if not r.startswith("#"))
    for r in rdr:
        rows.append(r)

pred_rows = [r for r in rows if r["mp_id"].startswith("mp-")]
print(f"[s3b] {len(rows)} validated rows; {len(pred_rows)} predictable (MP structure exists)")

from mp_api.client import MPRester  # noqa: E402
structs = {}
with MPRester(KEY) as mpr:
    for r in pred_rows:
        structs[r["mp_id"]] = mpr.get_structure_by_material_id(r["mp_id"])
print(f"[s3b] fetched {len(structs)} structures")

from src.qme_inference import predict_from_structure  # noqa: E402
out_rows = []
for r in pred_rows:
    mid, vlit = r["mp_id"], float(r["V_lit"])
    s = structs[mid]
    res = predict_from_structure(s.as_dict())
    vp = res.get("voltage")
    if vp is None:
        out_rows.append({"mp_id": mid, "formula": r["formula"], "polymorph": r["polymorph"],
                         "family": r["family"], "tier": r["tier"], "v_lit": vlit,
                         "v_pred": None, "reason": str(res.get("reason", ""))[:120]})
        continue
    vp = float(vp)
    row = {"mp_id": mid, "formula": r["formula"], "polymorph": r["polymorph"],
           "family": r["family"], "tier": r["tier"], "v_lit": vlit,
           "v_pred": round(vp, 4), "signed_err": round(vp - vlit, 4),
           "abs_err": round(abs(vp - vlit), 4), "nsites": len(s), "reason": ""}
    if mid in V_MP:
        row["v_mp"] = V_MP[mid]
        row["pred_minus_mp"] = round(vp - V_MP[mid], 4)
        row["mp_minus_lit"] = round(V_MP[mid] - vlit, 4)
        row["pred_minus_lit"] = round(vp - vlit, 4)
        row["repro_prior_pred"] = V_PRED_PRIOR[mid]
        row["repro_delta"] = round(vp - V_PRED_PRIOR[mid], 4)
    out_rows.append(row)

ok = [r for r in out_rows if r["v_pred"] is not None]

def mae(e): return float(np.mean(np.abs(e)))
def rmse(e): return float(np.sqrt(np.mean(np.asarray(e) ** 2)))

def boot_ci_mae(errs, n=N_BOOT):
    errs = np.asarray(errs, dtype=float)
    if len(errs) < 2:
        return None, None
    idx = RNG.integers(0, len(errs), size=(n, len(errs)))
    maes = np.abs(errs[idx]).mean(axis=1)
    return float(np.percentile(maes, 2.5)), float(np.percentile(maes, 97.5))

def loocv_corrected(signed):
    """LOOCV additive bias correction: row i corrected by mean signed error of the others."""
    signed = np.asarray(signed, dtype=float)
    n = len(signed)
    out = np.empty(n)
    for i in range(n):
        bias = (signed.sum() - signed[i]) / (n - 1)
        out[i] = signed[i] - bias
    return out

def block(rows_, label):
    if not rows_:
        return {"label": label, "n": 0}
    signed = np.array([r["signed_err"] for r in rows_])
    corrected = loocv_corrected(signed) if len(signed) >= 3 else None
    lo, hi = boot_ci_mae(signed)
    d = {"label": label, "n": len(rows_),
         "raw_MAE_V": round(mae(signed), 4), "raw_RMSE_V": round(rmse(signed), 4),
         "raw_bias_V": round(float(signed.mean()), 4),
         "raw_MAE_boot95_V": [round(lo, 4), round(hi, 4)] if lo is not None else None}
    if corrected is not None:
        clo, chi = boot_ci_mae(corrected)
        d["loocv_corrected_MAE_V"] = round(mae(corrected), 4)
        d["loocv_corrected_RMSE_V"] = round(rmse(corrected), 4)
        d["loocv_corrected_MAE_boot95_V"] = [round(clo, 4), round(chi, 4)]
    return d

held = ok  # every predictable row is in_training_corpus=False (verified)
no_c = [r for r in held if r["tier"] != "C"]
phos = [r for r in held if r["family"] == "polyanionic_phosphate"]
phos_no_c = [r for r in phos if r["tier"] != "C"]

vlits = np.array([r["v_lit"] for r in held])
signed = np.array([r["signed_err"] for r in held])
vdep = float(np.corrcoef(vlits, signed)[0, 1]) if len(held) >= 3 else None

summary = {
    "test": "Step 3b MACHINE-CURATED literature validation: GNN (active qme-v2.5-battery) vs experimental V_avg",
    "curation": "MACHINE-CURATED 2026-06-09, pending operator spot-check",
    "n_validated_rows": len(rows),
    "n_predictable": len(pred_rows),
    "n_predicted": len(ok),
    "n_excluded_no_mp_structure": len(rows) - len(pred_rows),
    "all_rows_held_out": True,
    "blocks": {
        "held_out_all": block(held, "held-out, all tiers"),
        "held_out_no_tierC": block(no_c, "held-out, Tier A/B only"),
        "phosphate_all": block(phos, "polyanionic_phosphate, all tiers"),
        "phosphate_no_tierC": block(phos_no_c, "polyanionic_phosphate, Tier A/B only"),
    },
    "voltage_dependence_pearson_r_signedErr_vs_Vlit": round(vdep, 3) if vdep is not None else None,
    "three_way_decomposition": [
        {k: r[k] for k in ("mp_id", "formula", "polymorph", "v_pred", "v_mp", "v_lit",
                           "pred_minus_mp", "mp_minus_lit", "pred_minus_lit",
                           "repro_prior_pred", "repro_delta")}
        for r in held if "v_mp" in r
    ],
    "step2_family_bias_context_V": 0.2022,
}

(HERE / "s3b_litexp_summary.json").write_text(json.dumps(summary, indent=2))
fields = ["mp_id", "formula", "polymorph", "family", "tier", "v_lit", "v_pred", "signed_err",
          "abs_err", "v_mp", "pred_minus_mp", "mp_minus_lit", "pred_minus_lit",
          "repro_prior_pred", "repro_delta", "nsites", "reason"]
with open(HERE / "s3b_litexp_results.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for r in out_rows:
        w.writerow({k: r.get(k, "") for k in fields})

print(json.dumps(summary, indent=2))
