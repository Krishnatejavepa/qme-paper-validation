#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""
D1 offset audit: final verdict at the cutoff-converged (ecutwfc=70 / ecutrho=560 Ry)
energies. Committed provenance for the arXiv v2 Results C numbers.

WHY THIS EXISTS
The pre-registration (prereg/D1_PREREGISTRATION_2026-06-10.md) fixed the run parameters at
the anchor scale ecutwfc=50 / ecutrho=200 Ry. During execution the 200 Ry charge-density
cutoff proved numerically unconverged for this audit: the LiFePO4 cell relaxed to a
spuriously large volume (voltage inflated ~0.6 V), the Li2FeP2O7 relaxation did not
converge, and even LiCoO2 shifted ~0.19 V. All four couples were therefore re-relaxed at
a converged cutoff (70/560 Ry; LiCoO2 additionally verified stable to 4 mV at 720 Ry).
This deviation from the pre-registered cutoff is disclosed in the paper (Results C); the
gate OUTCOME (FAIL) is invariant to it (sd >> 0.30 V at 200 Ry as well).

This script does NOT modify the published results.json (which preserves the 200 Ry
record). It overlays the 70/560 Final-enthalpy energies onto an in-memory copy and runs
the committed gate logic in d1_audit.compute_offsets, then writes
d1_corrected_offsets.json into data/.

PROVENANCE (Final enthalpy after `bfgs converged`, or accepted force-plateau endpoint;
QE 7.3.1, HUBBARD ortho-atomic, ecutwfc=70 / ecutrho=560 Ry; logs under ~/.qme_loop/work/):
  LiFePO4   -2099.2391951526  bfgs-converged   D1_PHASE2_OLIVINE_20260625/p2_lifepo4_li.out
  FePO4     -2040.1923843303  bfgs-converged   D1_PHASE2_OLIVINE_20260625/p2_fepo4_de.out
  Li2FeP2O7 -2714.91601645    accepted F=0.0055 D1_PHASE3_PYRO_20260625/p3_li2fep2o7_li.out
  LiFeP2O7  -2655.86924534    accepted F=0.0061 D1_PHASE3_PYRO_20260625/p3_lifep2o7_li.out
  LiMn2O4   -1207.2552580590  bfgs-converged   D1_PHASE5_SPINEL_20260627/p5_limn2o4_li.out
  lambda-MnO2 -1177.7438928089 bfgs-converged  D1_PHASE5_SPINEL_20260627/p5_lmno2_de.out
  LiCoO2    -396.3241015149   bfgs-converged   D1_PHASE6_LICOO2_20260628/p6_licoo2_li.out
  CoO2      -381.5344673348   bfgs-converged   D1_PHASE6_LICOO2_20260628/p6_licoo2_de.out

bfgs_converged is left FALSE for the two force-plateaued phosphate endpoints, with
accepted=true + accepted_reason (acceptance-with-disclosure; the honest flag is not
flipped). Pair B is admitted to the gate via ledger_admissible=True after the
ground-state sensitivity check cleared at the converged cutoff.

Run:  python scripts/d1_offset_verdict_70_560.py
"""
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d1_audit as da  # noqa: E402

# 70/560 Final-enthalpy energies (Ry) overlaid onto the published 200 Ry record.
CORR = {
    "d1_lifepo4_li":   dict(total_energy_ry=-2099.2391951526, bfgs_converged=True,  accepted=False, total_magnetization=16.0),
    "d1_fepo4_de":     dict(total_energy_ry=-2040.1923843303, bfgs_converged=True,  accepted=False, total_magnetization=20.0),
    "d1_li2fep2o7_li": dict(total_energy_ry=-2714.91601645,   bfgs_converged=False, accepted=True,  total_magnetization=16.0,
                            accepted_reason="cutoff-converged 70/560 re-relax; force-plateau 0.0055 Ry/au in soft basin",
                            ledger_admissible=True),
    "d1_lifep2o7_li":  dict(total_energy_ry=-2655.86924534,   bfgs_converged=False, accepted=True,  total_magnetization=20.0,
                            accepted_reason="cutoff-converged 70/560 re-relax; force-plateau 0.0061 Ry/au in soft basin"),
    "d1_limn2o4_li":   dict(total_energy_ry=-1207.2552580590, bfgs_converged=True,  accepted=False, total_magnetization=14.0),
    "d1_lmno2_de":     dict(total_energy_ry=-1177.7438928089, bfgs_converged=True,  accepted=False, total_magnetization=12.0),
}

# LiCoO2 anchor re-run at 70/560 (QE 7.x, nspin=1): V from the same formula d1_audit uses.
E_LICOO2_LI, E_COO2_DE = -396.3241015149, -381.5344673348
da.V_QME_LICOO2 = round(-((E_LICOO2_LI) - (E_COO2_DE) - 1 * da.MU_LI) * da.RY_TO_EV / 1, 4)


def build_corrected_set():
    base = da.load_results()
    present = {e.get("id") for e in base if e.get("id")}
    out = []
    for e in base:
        jid = e.get("id")
        if jid in CORR:
            e2 = dict(e)
            e2.update(CORR[jid])
            e2.pop("ground_state_pending", None)
            out.append(e2)
        else:
            out.append(e)
    for jid, fields in CORR.items():
        if jid not in present:
            out.append(dict(id=jid, **fields))
    return out


def robustness_200ry():
    """Dispersion of the evaluable couples at the pre-registered 200 Ry cutoff
    (the published runpod_data/results.json), to show the FAIL verdict is
    invariant to the cutoff change. Pair B is provenance-held at 200 Ry
    (non-convergence), so this is over the evaluable couples only."""
    base = da.load_results()              # 200 Ry published record, V_QME_LICOO2=4.120
    da_v = da.V_QME_LICOO2
    da.V_QME_LICOO2 = 4.120
    a = da.compute_offsets(base)
    da.V_QME_LICOO2 = da_v                # restore the 70/560 LiCoO2 voltage
    evaluable = {k: round(v, 4) for k, v in a["offsets"].items()}
    sd = statistics.stdev(list(evaluable.values())) if len(evaluable) >= 2 else None
    return {"cutoff_ry": 200, "evaluable_offsets": evaluable,
            "sd": round(sd, 4) if sd else None,
            "note": "pair B provenance-held (non-convergence) at 200 Ry; "
                    "dispersion already far above the 0.30 V bar."}


def main():
    rob = robustness_200ry()
    analysis = da.compute_offsets(build_corrected_set())
    offsets = {k: round(v, 4) for k, v in analysis["offsets"].items()}
    core = [analysis["offsets"][k]
            for k in ("LiCoO2", "pairA_LiFePO4", "pairB_Li2FeP2O7")
            if k in analysis["offsets"]]
    core_sd = statistics.stdev(core)
    core_mean = statistics.mean(core)

    artifact = {
        "description": "D1 offset audit verdict at the cutoff-converged 70/560 Ry energies "
                       "(arXiv v2 Results C). Generated by tasks/d1_offset_verdict_70_560.py.",
        "cutoff": {"ecutwfc_ry": 70, "ecutrho_ry": 560,
                   "licoo2_stability_check_ry": 720, "licoo2_drift_at_720_mv": 4},
        "preregistration_deviation": "Pre-registered cutoff was 50/200 Ry; recomputed at "
                                     "70/560 Ry because 200 Ry was numerically unconverged "
                                     "(LiFePO4 cell runaway ~+0.6 V, Li2FeP2O7 non-convergence, "
                                     "LiCoO2 ~0.19 V shift). FAIL verdict is invariant to the cutoff.",
        "mu_li_ry": da.MU_LI,
        "ry_to_ev": da.RY_TO_EV,
        "v_qme_licoo2": da.V_QME_LICOO2,
        "v_exp": {k: da.V_EXP[k] for k in ("LiCoO2", "pairA_LiFePO4",
                                           "pairB_Li2FeP2O7", "pairC_LiMn2O4")},
        "offsets": offsets,
        "n_evaluated": analysis["n_evaluated"],
        "mean_delta": round(analysis["mean_delta"], 4),
        "sd": round(analysis["sd"], 4),
        "gate_status": analysis["gate_status"],
        "verdict": analysis["verdict"],
        "core_n3": {"keys": ["LiCoO2", "pairA_LiFePO4", "pairB_Li2FeP2O7"],
                    "mean": round(core_mean, 4), "sd": round(core_sd, 4),
                    "verdict": "PASS" if core_sd < 0.15 else ("FAIL" if core_sd >= 0.30 else "GRAY")},
        "robustness_at_preregistered_200ry": rob,
        "energies_ry_70_560": {k: v["total_energy_ry"] for k, v in CORR.items()},
        "provenance_logs": "~/.qme_loop/work/D1_PHASE{2,3,5,6}_*  (Final enthalpy / accepted endpoint)",
    }

    _root = Path(os.environ.get("QME_ROOT", Path(__file__).resolve().parents[1]))
    out_path = _root / "data" / "d1_corrected_offsets.json"
    out_path.write_text(json.dumps(artifact, indent=2) + "\n")

    print(da.format_analysis_report(analysis))
    print(f"\n[gate_status={analysis['gate_status']}  verdict={analysis['verdict']}  "
          f"sd={analysis['sd']:.4f}  mean={analysis['mean_delta']:.4f}  n={analysis['n_evaluated']}]")
    print("OFFSETS:", offsets)
    print(f"CORE n=3: mean={core_mean:+.4f}  sd={core_sd:.4f}  "
          f"-> {artifact['core_n3']['verdict']}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
