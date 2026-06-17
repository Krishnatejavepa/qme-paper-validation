# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""
PROVENANCE / PRE-REGISTERED STUB, NOT part of the clean-room reproduce set.
This is the Branch-B (Sec. VI) calibration-audit analysis, committed BEFORE any
result exists. It reads runtime scheduler output (runpod_data/results.json) and
the QME `config` module, neither of which is shipped, and it deliberately
refuses to run on an n_Li mismatch. No D1 verdict exists at submission, so no
number from it appears in the paper. Shipped to document the pre-registered gate.

D1 offset audit, analysis (STUB, committed BEFORE results exist).

Pre-registered protocol: D1_PREREGISTRATION_2026-06-10.md (workspace root).
Reads runpod_data/results.json (the scheduler's ground-truth output), enforces
HARD n_Li assertions against the staged input cells, computes the offset
distribution delta_i = V_QME - V_exp, and applies the PRE-REGISTERED gate:

    PASS  sd(delta) < 0.15 V   -> scale calibratable (publish with offset + error bars)
    FAIL  sd(delta) >= 0.30 V  -> absolute-voltage claims retired (ranking-only)
    GRAY  otherwise            -> operator decision, documented at sync time

LiMn2O4 is the pre-registered STRETCH point: if either Mn half is missing,
unconverged, or outside its registered spin manifold, the verdict is issued on
the n=3 core (LiCoO2 + pair A + pair B) and the Mn point reported as excluded.

This stub runs safely before results exist (reports what is pending and exits 0).
"""

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

RY_TO_EV = 13.605693122994
MU_LI = -14.4725646547          # in-DB BCC Li reference (state='reference')

RESULTS_JSON = Path(config.QME_ROOT) / "runpod_data" / "results.json"
INPUT_DIR = Path(config.WORK_DIR) / "inputs"

# (job, registered nat, registered n_Li), from D1_PREREGISTRATION_2026-06-10.md
REGISTERED_CELLS = {
    "d1_lifepo4_li":   (28, 4),
    "d1_fepo4_de":     (24, 0),
    "d1_li2fep2o7_li": (48, 8),
    "d1_lifep2o7_li":  (44, 4),
    "d1_limn2o4_li":   (14, 2),
    "d1_lmno2_de":     (12, 0),
}

V_EXP = {"LiCoO2": 4.0, "pairA_LiFePO4": 3.45, "pairB_Li2FeP2O7": 3.5, "pairC_LiMn2O4": 4.05}
V_QME_LICOO2 = 4.120  # existing anchor (qme.db verified_results, candidate 1)

# Registered spin manifolds (|total magnetization|, Bohr), pair point excluded on mismatch
REGISTERED_MAG = {
    "d1_lifepo4_li": 16.0, "d1_fepo4_de": 20.0,
    "d1_li2fep2o7_li": 16.0, "d1_lifep2o7_li": 20.0,
    "d1_limn2o4_li": 14.0, "d1_lmno2_de": 12.0,
}
MAG_TOL = 0.05  # Bohr; integer-manifold check (spin-slosh guard)


def count_cell(job: str):
    """Count nat and n_Li from the ACTUAL staged input file (never the formula)."""
    text = (INPUT_DIR / f"{job}.in").read_text()
    nat = int(text.split("nat =")[1].split()[0]) if "nat =" in text else int(
        text.split("nat=")[1].split()[0])
    n_li, in_pos = 0, False
    for line in text.splitlines():
        if line.strip().startswith("ATOMIC_POSITIONS"):
            in_pos = True
            continue
        if in_pos:
            parts = line.split()
            if not parts or not parts[0].isalpha() or parts[0] in ("K_POINTS",):
                in_pos = False
                continue
            if parts[0] == "Li":
                n_li += 1
    return nat, n_li


def hard_nli_checks():
    """HARD assertions: staged cells must match the pre-registered bookkeeping."""
    for job, (nat_reg, nli_reg) in REGISTERED_CELLS.items():
        nat, nli = count_cell(job)
        assert nat == nat_reg, f"{job}: nat {nat} != registered {nat_reg}, STOP, do not compute voltages"
        assert nli == nli_reg, f"{job}: n_Li {nli} != registered {nli_reg}, STOP, do not compute voltages"
    # pair B is two different cells; both must be exactly 4 f.u.
    assert REGISTERED_CELLS["d1_li2fep2o7_li"] == (48, 8)   # Li2FeP2O7: 12 atoms/f.u. * 4
    assert REGISTERED_CELLS["d1_lifep2o7_li"] == (44, 4)    # LiFeP2O7: 11 atoms/f.u. * 4
    print("HARD n_Li checks: all 6 staged cells match the pre-registration.")


def get(results: list, job: str):
    for e in results:
        if e.get("id") == job and e.get("bfgs_converged"):
            return e
    return None


def spin_ok(entry: dict, job: str) -> bool:
    mag = entry.get("total_magnetization")
    if mag is None:
        print(f"  WARNING {job}: no magnetization recorded, treating as manifold-unverified")
        return False
    return abs(abs(mag) - REGISTERED_MAG[job]) <= MAG_TOL


def main():
    hard_nli_checks()
    results = json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else []

    offsets = {"LiCoO2": V_QME_LICOO2 - V_EXP["LiCoO2"]}
    pending = []

    # Pair A: same cell, delta n = 4
    a1, a2 = get(results, "d1_lifepo4_li"), get(results, "d1_fepo4_de")
    if a1 and a2:
        if spin_ok(a1, "d1_lifepo4_li") and spin_ok(a2, "d1_fepo4_de"):
            v = -(a1["total_energy_ry"] - a2["total_energy_ry"] - 4 * MU_LI) * RY_TO_EV / 4
            offsets["pairA_LiFePO4"] = v - V_EXP["pairA_LiFePO4"]
            print(f"pair A  LiFePO4: V = {v:.4f} V (exp 3.45) -> delta = {offsets['pairA_LiFePO4']:+.4f} V")
        else:
            print("pair A: EXCLUDED (outside registered spin manifold)")
    else:
        pending.append("pair A (LiFePO4/FePO4)")

    # Pair B: different cells, both 4 f.u., delta n = 1 per f.u.
    b1, b2 = get(results, "d1_li2fep2o7_li"), get(results, "d1_lifep2o7_li")
    if b1 and b2:
        if spin_ok(b1, "d1_li2fep2o7_li") and spin_ok(b2, "d1_lifep2o7_li"):
            v = -(b1["total_energy_ry"] / 4 - b2["total_energy_ry"] / 4 - MU_LI) * RY_TO_EV
            offsets["pairB_Li2FeP2O7"] = v - V_EXP["pairB_Li2FeP2O7"]
            print(f"pair B  Li2FeP2O7: V = {v:.4f} V (exp 3.5) -> delta = {offsets['pairB_Li2FeP2O7']:+.4f} V")
        else:
            print("pair B: EXCLUDED (outside registered spin manifold)")
    else:
        pending.append("pair B (Li2FeP2O7/LiFeP2O7)")

    # Pair C (STRETCH): same cell, delta n = 2
    c1, c2 = get(results, "d1_limn2o4_li"), get(results, "d1_lmno2_de")
    if c1 and c2:
        if spin_ok(c1, "d1_limn2o4_li") and spin_ok(c2, "d1_lmno2_de"):
            v = -(c1["total_energy_ry"] - c2["total_energy_ry"] - 2 * MU_LI) * RY_TO_EV / 2
            offsets["pairC_LiMn2O4"] = v - V_EXP["pairC_LiMn2O4"]
            print(f"pair C  LiMn2O4 (stretch): V = {v:.4f} V (exp 4.05) -> delta = {offsets['pairC_LiMn2O4']:+.4f} V")
        else:
            print("pair C (stretch): EXCLUDED per pre-registration (spin manifold)")
    else:
        pending.append("pair C (LiMn2O4/lambda-MnO2, stretch)")

    print(f"\nLiCoO2 (existing): V = {V_QME_LICOO2} V (exp 4.0) -> delta = {offsets['LiCoO2']:+.4f} V")

    if pending:
        print(f"\nPENDING ({len(pending)}): " + "; ".join(pending))
        print("Gate NOT evaluated, waiting for the queue. (This is the pre-results stub path.)")
        return 0

    deltas = list(offsets.values())
    n = len(deltas)
    mean = statistics.mean(deltas)
    sd = statistics.stdev(deltas)
    print(f"\nOFFSET DISTRIBUTION (n={n}): mean = {mean:+.4f} V, sd = {sd:.4f} V")
    if sd < 0.15:
        print("PRE-REGISTERED GATE: PASS, scale calibratable (sd < 0.15 V).")
    elif sd >= 0.30:
        print("PRE-REGISTERED GATE: FAIL, retire absolute-voltage claims (sd >= 0.30 V).")
    else:
        print("PRE-REGISTERED GATE: GRAY ZONE, operator decision required (0.15 <= sd < 0.30 V).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
