# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""
D1 offset audit helpers (gate logic for the Results C verdict).

Vendored from the engine's src/d1_audit.py. Only the path resolution was
changed to be repo-relative (the original imported the engine config module);
the compute and gate logic is unchanged.

Pre-registered protocol: prereg/D1_PREREGISTRATION_2026-06-10.md
"""

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path
from typing import Any

RY_TO_EV = 13.605693122994
MU_LI = -14.4725646547

# Repo root: <root>/scripts/d1_audit.py. Override with $QME_ROOT, matching the
# other scripts in this directory.
_ROOT = Path(os.environ.get("QME_ROOT", Path(__file__).resolve().parents[1]))
RESULTS_JSON = _ROOT / "data" / "results.json"
INPUT_DIR = _ROOT / "data" / "inputs"

D1_JOBS = (
    "d1_lifepo4_li",
    "d1_fepo4_de",
    "d1_li2fep2o7_li",
    "d1_lifep2o7_li",
    "d1_limn2o4_li",
    "d1_lmno2_de",
)

REGISTERED_CELLS = {
    "d1_lifepo4_li": (28, 4),
    "d1_fepo4_de": (24, 0),
    "d1_li2fep2o7_li": (48, 8),
    "d1_lifep2o7_li": (44, 4),
    "d1_limn2o4_li": (14, 2),
    "d1_lmno2_de": (12, 0),
}

V_EXP = {
    "LiCoO2": 4.0,
    "pairA_LiFePO4": 3.45,
    "pairB_Li2FeP2O7": 3.5,
    "pairC_LiMn2O4": 4.05,
}
V_QME_LICOO2 = 4.120

REGISTERED_MAG = {
    "d1_lifepo4_li": 16.0,
    "d1_fepo4_de": 20.0,
    "d1_li2fep2o7_li": 16.0,
    "d1_lifep2o7_li": 20.0,
    "d1_limn2o4_li": 14.0,
    "d1_lmno2_de": 12.0,
}
MAG_TOL = 0.05

# Jobs blocked from the offset ledger until operator clears provenance gates.
LEDGER_PENDING_JOBS = frozenset({"d1_li2fep2o7_li"})


def is_usable_entry(entry: dict[str, Any] | None) -> bool:
    """Energy is usable if BFGS converged OR operator accepted with disclosure."""
    if not entry:
        return False
    if entry.get("bfgs_converged"):
        return entry.get("total_energy_ry") is not None
    return bool(entry.get("accepted")) and entry.get("total_energy_ry") is not None


def is_ledger_admissible(entry: dict[str, Any], job_id: str) -> bool:
    """False when a result exists but must not enter the offset ledger yet."""
    if job_id in LEDGER_PENDING_JOBS:
        if entry.get("ledger_admissible") is False:
            return False
        if entry.get("ground_state_pending"):
            return False
        reason = (entry.get("accepted_reason") or "").lower()
        if "ground-state" in reason and "pending" in reason:
            return False
    return True


def get_magnetization(entry: dict[str, Any]) -> float | None:
    for key in ("total_magnetization", "total_magnetization_bohr"):
        if entry.get(key) is not None:
            return float(entry[key])
    return None


def spin_ok(entry: dict[str, Any], job: str) -> bool:
    mag = get_magnetization(entry)
    if mag is None:
        return False
    return abs(abs(mag) - REGISTERED_MAG[job]) <= MAG_TOL


def load_results(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or RESULTS_JSON
    if not p.exists():
        return []
    return json.loads(p.read_text())


def find_raw_result(results: list[dict[str, Any]], job: str) -> dict[str, Any] | None:
    for entry in results:
        if entry.get("id") == job:
            return entry
    return None


def find_result(results: list[dict[str, Any]], job: str) -> dict[str, Any] | None:
    for entry in results:
        if entry.get("id") != job:
            continue
        if not is_usable_entry(entry):
            continue
        if not is_ledger_admissible(entry, job):
            continue
        return entry
    return None


def job_status(entry: dict[str, Any] | None) -> str:
    if entry is None:
        return "pending"
    if not is_usable_entry(entry):
        return "running_or_incomplete"
    job_id = entry.get("id", "")
    if not is_ledger_admissible(entry, job_id):
        return "usable_ledger_blocked"
    if entry.get("bfgs_converged"):
        return "converged"
    if entry.get("accepted"):
        return "accepted_force_plateau"
    return "unknown"


def summarize_d1_queue(results: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Per-job D1 status for CLI / monitoring."""
    results = results if results is not None else load_results()
    by_id = {e["id"]: e for e in results if e.get("id")}
    rows = []
    for job in D1_JOBS:
        entry = by_id.get(job)
        rows.append(
            {
                "job": job,
                "status": job_status(entry),
                "bfgs_converged": bool(entry.get("bfgs_converged")) if entry else False,
                "accepted": bool(entry.get("accepted")) if entry else False,
                "ledger_admissible": (
                    is_ledger_admissible(entry, job) if entry and is_usable_entry(entry) else None
                ),
                "mag": get_magnetization(entry) if entry else None,
            }
        )
    return rows


def compute_offsets(results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Compute offset deltas and pre-registered gate verdict.
    Returns a structured dict safe for CLI JSON output and unit tests.
    """
    results = results if results is not None else load_results()
    offsets: dict[str, float] = {"LiCoO2": V_QME_LICOO2 - V_EXP["LiCoO2"]}
    pending: list[str] = []
    excluded: list[str] = []
    pair_voltages: dict[str, float] = {}

    def _pair(
        key: str,
        label: str,
        job_a: str,
        job_b: str,
        voltage_fn,
        *,
        stretch: bool = False,
    ):
        a, b = find_result(results, job_a), find_result(results, job_b)
        if not a or not b:
            pending.append(label)
            return
        if not spin_ok(a, job_a) or not spin_ok(b, job_b):
            excluded.append(f"{label} (spin manifold)")
            return
        v = voltage_fn(a, b)
        pair_voltages[key] = v
        offsets[key] = v - V_EXP[key]
        if stretch and key not in offsets:
            excluded.append(label)

    _pair(
        "pairA_LiFePO4",
        "pair A (LiFePO4/FePO4)",
        "d1_lifepo4_li",
        "d1_fepo4_de",
        lambda a, b: -(a["total_energy_ry"] - b["total_energy_ry"] - 4 * MU_LI) * RY_TO_EV / 4,
    )

    b1_raw = find_raw_result(results, "d1_li2fep2o7_li")
    b2_raw = find_raw_result(results, "d1_lifep2o7_li")
    if not is_usable_entry(b1_raw) or not is_usable_entry(b2_raw):
        pending.append("pair B (Li2FeP2O7/LiFeP2O7)")
    elif not is_ledger_admissible(b1_raw, "d1_li2fep2o7_li"):
        excluded.append("pair B (Li2FeP2O7/LiFeP2O7), ground-state check PENDING")
    elif spin_ok(b1_raw, "d1_li2fep2o7_li") and spin_ok(b2_raw, "d1_lifep2o7_li"):
        v = -(b1_raw["total_energy_ry"] / 4 - b2_raw["total_energy_ry"] / 4 - MU_LI) * RY_TO_EV
        pair_voltages["pairB_Li2FeP2O7"] = v
        offsets["pairB_Li2FeP2O7"] = v - V_EXP["pairB_Li2FeP2O7"]
    else:
        excluded.append("pair B (spin manifold)")

    _pair(
        "pairC_LiMn2O4",
        "pair C (LiMn2O4/lambda-MnO2, stretch)",
        "d1_limn2o4_li",
        "d1_lmno2_de",
        lambda a, b: -(a["total_energy_ry"] - b["total_energy_ry"] - 2 * MU_LI) * RY_TO_EV / 2,
        stretch=True,
    )

    core_keys = [k for k in ("LiCoO2", "pairA_LiFePO4", "pairB_Li2FeP2O7") if k in offsets]
    stretch_included = "pairC_LiMn2O4" in offsets

    verdict = None
    sd = mean = None
    n_eval = len(core_keys)

    pair_b_provenance_hold = (
        "pairB_Li2FeP2O7" not in offsets
        and any("ground-state check PENDING" in x for x in excluded)
    )

    if pending and not core_keys:
        gate_status = "waiting"
    elif pending:
        gate_status = "partial"
    elif pair_b_provenance_hold:
        gate_status = "provenance_hold"
    else:
        gate_status = "ready"
        eval_keys = core_keys.copy()
        if stretch_included:
            eval_keys.append("pairC_LiMn2O4")
        deltas = [offsets[k] for k in eval_keys]
        n_eval = len(deltas)
        mean = statistics.mean(deltas)
        sd = statistics.stdev(deltas) if n_eval > 1 else 0.0
        if sd < 0.15:
            verdict = "PASS"
        elif sd >= 0.30:
            verdict = "FAIL"
        else:
            verdict = "GRAY"

    return {
        "offsets": offsets,
        "pair_voltages": pair_voltages,
        "pending": pending,
        "excluded": excluded,
        "gate_status": gate_status,
        "verdict": verdict,
        "sd": sd,
        "mean_delta": mean,
        "n_evaluated": n_eval,
        "stretch_included": stretch_included,
        "queue": summarize_d1_queue(results),
    }


def format_analysis_report(analysis: dict[str, Any]) -> str:
    """Human-readable report for terminal / logs."""
    lines = []
    for row in analysis["queue"]:
        flag = ""
        if row["status"] == "accepted_force_plateau":
            flag = " [accepted, force-plateaued]"
        elif row["status"] == "usable_ledger_blocked":
            flag = " [ledger blocked, provenance gate]"
        lines.append(f"  {row['job']}: {row['status']}{flag}")

    for key, delta in analysis["offsets"].items():
        v = analysis["pair_voltages"].get(key)
        exp = V_EXP.get(key)
        if v is not None and exp is not None:
            lines.append(f"{key}: V={v:.4f} V (exp {exp}) -> delta={delta:+.4f} V")
        elif key == "LiCoO2":
            lines.append(f"LiCoO2: V={V_QME_LICOO2} V (exp {V_EXP['LiCoO2']}) -> delta={delta:+.4f} V")

    if analysis["excluded"]:
        lines.append("\nEXCLUDED:")
        for item in analysis["excluded"]:
            lines.append(f"  - {item}")

    if analysis["pending"]:
        lines.append(f"\nPENDING ({len(analysis['pending'])}): " + "; ".join(analysis["pending"]))
        lines.append("Gate NOT evaluated, waiting for queue completion.")
        return "\n".join(lines)

    if analysis["gate_status"] == "provenance_hold":
        lines.append(
            "\nPROVENANCE HOLD, pair B blocked until job-3 ground-state check clears "
            "(see RESTART_PROVENANCE.md). Gate NOT evaluated."
        )
        return "\n".join(lines)

    if analysis["gate_status"] == "ready" and analysis["verdict"]:
        lines.append(
            f"\nOFFSET DISTRIBUTION (n={analysis['n_evaluated']}): "
            f"mean={analysis['mean_delta']:+.4f} V, sd={analysis['sd']:.4f} V"
        )
        if analysis["verdict"] == "PASS":
            lines.append("PRE-REGISTERED GATE: PASS, scale calibratable (sd < 0.15 V).")
        elif analysis["verdict"] == "FAIL":
            lines.append("PRE-REGISTERED GATE: FAIL, retire absolute-voltage claims (sd >= 0.30 V).")
        else:
            lines.append("PRE-REGISTERED GATE: GRAY ZONE, operator decision required.")

    return "\n".join(lines)
