# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""Phase-6 consistency sweep: abstract == body == figures == CLAIMS_MAP.

Loads the committed artifacts, derives the exact strings the paper must
contain (body precision and the operator-approved abstract roundings), and
verifies each appears in paper.tex or the generated table fragments. Exits
nonzero on any miss. Figures are checked by their own scripts' guards
(fig2 recomputes r against the committed value before drawing).
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("QME_ROOT", HERE.parent))
NWD = ROOT / "data"
GNOME = ROOT / "data"
DB = ROOT / "db" / "qme.db"
PAPER = ROOT / "paper"

paper = (PAPER / "paper.tex").read_text()
tables = "".join(p.read_text()
                 for p in sorted((PAPER / "tables").glob("*.tex")))
hay = paper + tables

s3b = json.loads((NWD / "s3b_litexp_summary.json").read_text())
st2 = json.loads((NWD / "step2_summary.json").read_text())
q1 = json.loads((NWD / "q1_oos_summary.json").read_text())
q2 = json.loads((NWD / "q2_collapse_summary.json").read_text())
g1 = json.loads((GNOME / "gnome_screen_summary.json").read_text())
g3 = json.loads((GNOME / "gnome_triage_probe_summary.json").read_text())

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
volts = [str(r[0]) for r in con.execute(
    "SELECT voltage_computed FROM verified_results ORDER BY id")]
con.close()

b6 = s3b["blocks"]["held_out_no_tierC"]
b7 = s3b["blocks"]["held_out_all"]
dec = s3b["three_way_decomposition"]

checks = []  # (label, expected-string)

def add(label, value):
    checks.append((label, value))

# Headline (body precision)
add("raw MAE n=6", f"{b6['raw_MAE_V']:.3f}")              # 0.668
add("corr MAE n=6", f"{b6['loocv_corrected_MAE_V']:.3f}")  # 0.802
add("primary upper CI", f"{b6['loocv_corrected_MAE_boot95_V'][1]:.3f}")  # 1.092
add("raw bias n=6", f"{b6['raw_bias_V']:+.3f}".replace("+0", "+0"))      # +0.231
add("n=7 raw", f"{b7['raw_MAE_V']:.3f}")                   # 0.694
add("n=7 corr", f"{b7['loocv_corrected_MAE_V']:.3f}")      # 0.756
add("n=7 upper CI", f"{b7['loocv_corrected_MAE_boot95_V'][1]:.3f}")      # 1.017
add("pearson r", f"{s3b['voltage_dependence_pearson_r_signedErr_vs_Vlit']:.3f}")
# Abstract roundings (operator-approved at HALT-1)
add("abstract raw", f"{round(b6['raw_MAE_V'], 2)}")        # 0.67
add("abstract CI", f"{round(b6['loocv_corrected_MAE_boot95_V'][1], 2)}")  # 1.09
add("abstract r", "-0.94")
add("abstract MP offset", "0.54")
# Decomposition. Body carries the sign of the MP-vs-experiment offset in
# words ("below"), so magnitudes are checked; roundings follow the committed
# verdict report (ROUND_HALF_UP, e.g. -0.5375 -> 0.538, +0.1035 -> +0.104).
from decimal import Decimal, ROUND_HALF_UP

def rhu(v, nd="0.001"):
    return Decimal(str(v)).quantize(Decimal(nd), rounding=ROUND_HALF_UP)

add("ABW mp-lit magnitude", f"{abs(rhu(dec[0]['mp_minus_lit']))}")  # 0.539
add("beta mp-lit magnitude", f"{abs(rhu(dec[1]['mp_minus_lit']))}")  # 0.538
add("ABW pred-mp", f"{rhu(dec[0]['pred_minus_mp'])}")               # -0.245
add("beta pred-mp", f"+{rhu(dec[1]['pred_minus_mp'])}")             # +0.104
# NVPF's -0.09 V and the per-row -0.784 V live in Fig. 2 / the results CSV;
# prose scopes its sentence to the <3.5 V rows and the cobalt rows, so they
# are not asserted in the text.
add("repro ABW", f"{dec[0]['repro_delta']:.3f}")            # -0.011
add("repro beta", f"{dec[1]['repro_delta']:.3f}")           # -0.055
# Step-2 / OOS chain
add("oos raw MAE", f"{q1['MAE_V']:.4f}")                    # 0.5892
add("oos bias", f"{q1['mean_signed_err_bias_V']:.4f}")      # 0.4263
add("F1 spread", f"{st2['failure_modes']['F1_observed_spread_V']:.4f}")
add("LOFO point", f"{st2['primary_metric']['point_estimate_V']:.4f}")
add("LOFO resid bias", f"{st2['primary_metric']['residual_bias_V']:.4f}")
add("LOFO upper CI", f"{st2['primary_metric']['value_V']:.4f}")
for fam, key in [("other", "other"), ("phosphate", "polyanionic_phosphate"),
                 ("layered", "layered_oxide")]:
    add(f"bias {fam}", f"{st2['per_family_diagnostic'][key]['bias']:+.4f}")
# Saturation + GNoME
add("q2 enumerated", str(q2["n_distinct_enumerated"]))
add("q2 smact", str(q2["n_smact_valid_screened"]))
add("q2 flagged", str(q2["flagged_debunkable_as_known"]))
add("q2 pct", f"{q2['flagged_pct']}")
add("q2 survivors", str(q2["survivors_not_debunkable"]))
add("gnome pop", f"{g1['n_total_population']:,}".replace(",", "{,}"))
add("gnome funnel in", str(g3["funnel_narrowing_4a"]["N_input"]))
add("gnome after smact", str(g3["funnel_narrowing_4a"]["after_smact"]))
add("gnome after stab", str(g3["funnel_narrowing_4a"]["after_oracle_stability"]))
add("gnome survivors", str(g3["funnel_narrowing_4a"]["after_polaron_nonblocking"]))
add("gnome surv pct", f"{g3['funnel_narrowing_4a']['survivors_pct_of_input']}")
add("gnome dispute", f"{g3['echo_test_4c']['oracle_dispute_rate_pct']}")
# Ledger voltages (db)
for v in volts:
    add(f"ledger {v}", v if v != "4.12" else "4.120")
# Per-row signed errors (results CSV, via verdict-rounded forms in prose)
for s in ["+0.85", "+0.55", "-0.78", "-0.43", "+1.31", "+0.84"]:
    add(f"signed err {s}", s)
# Methods constants
add("mu_Li", "-14.4725646547")
add("mu_Na", "-95.34612073")
add("anchor-fit", "0.084")
add("graphs", "2814")
# D1 gate
add("gate lo", "0.15")
add("gate hi", "0.3")

# D1 Results C: every number traces to the committed verdict artifact
# d1_corrected_offsets.json (generated by d1_offset_verdict_70_560.py).
d1 = json.loads((NWD / "d1_corrected_offsets.json").read_text())
_off = d1["offsets"]
add("d1 LiCoO2 offset", f"{round(_off['LiCoO2'], 2):+.2f}")          # +0.31
add("d1 LiFePO4 offset", f"{round(_off['pairA_LiFePO4'], 2):+.2f}")  # +0.48
add("d1 Li2FeP2O7 offset", f"{round(_off['pairB_Li2FeP2O7'], 2):+.2f}")  # +0.43
add("d1 LiMn2O4 offset", f"{round(_off['pairC_LiMn2O4'], 2):+.2f}")  # -0.20
add("d1 sd", f"{d1['sd']:.2f}")                                       # 0.31
add("d1 core sd", f"{d1['core_n3']['sd']:.2f}")                       # 0.09
add("d1 core mean", f"{d1['core_n3']['mean']:.2f}")                   # 0.41
add("d1 robustness sd 200Ry",
    f"{d1['robustness_at_preregistered_200ry']['sd']:.2f}")          # 0.68
add("d1 ecutrho", str(d1["cutoff"]["ecutrho_ry"]))                   # 560
add("d1 licoo2 720", str(d1["cutoff"]["licoo2_stability_check_ry"]))  # 720
add("d1 FAIL expressed as ranking-only", "ranking-only")            # paper renders FAIL verdict
assert d1["verdict"] == "FAIL", "D1 verdict is not FAIL, paper text assumes FAIL"
assert "does not yet exist" not in hay, \
    "stale pre-verdict phrasing 'does not yet exist' present; intro contradicts Results C/Table IV"

fails = []
for label, s in checks:
    variants = {s, s.replace("-", "$-$"), s.replace("-", "{-}")}
    if not any(v in hay for v in variants):
        fails.append((label, s))

print(f"consistency: {len(checks) - len(fails)}/{len(checks)} PASS")
for label, s in fails:
    print(f"  MISS [{label}]: {s!r}")
sys.exit(1 if fails else 0)
