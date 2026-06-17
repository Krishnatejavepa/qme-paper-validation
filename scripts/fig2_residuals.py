# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""F2, signed prediction error vs experimental voltage.

The committed correlation is r(signed err, V_lit) = -0.939 from
s3b_litexp_summary.json; this script re-computes it from the per-row CSV and
refuses to draw if the recomputation drifts from the committed artifact by
more than 0.002. The x-axis is V_lit, matching the artifact's own variable
(outline delta 2, operator-approved).
"""
import csv
import json
import sys

import numpy as np
import matplotlib.pyplot as plt

import qme_style as st

st.apply()

rows = []
with open(st.NWD / "s3b_litexp_results.csv") as f:
    for r in csv.DictReader(f):
        rows.append(r)

vlit = np.array([float(r["v_lit"]) for r in rows])
err = np.array([float(r["signed_err"]) for r in rows])

summary = json.loads((st.NWD / "s3b_litexp_summary.json").read_text())
r_committed = summary["voltage_dependence_pearson_r_signedErr_vs_Vlit"]
r_recomputed = float(np.corrcoef(err, vlit)[0, 1])
if abs(r_recomputed - r_committed) > 0.002:
    sys.exit(
        f"CONSISTENCY GUARD: recomputed r={r_recomputed:.4f} vs committed "
        f"{r_committed}, artifact drift, refusing to draw."
    )

fig, ax = plt.subplots(figsize=(st.SINGLE_COL, st.SINGLE_COL * 0.82))

ax.axhline(0.0, lw=0.7, color="0.55", ls="--", zorder=1)

# Per-point label offsets (dx pt, dy pt, ha) tuned against collisions.
OFFSETS = {
    "mp-19226": (6, 2, "left"),
    "mp-1203835": (6, 0, "left"),
    "mp-562796": (-6, 4, "right"),
    "mp-683773": (-6, 4, "right"),
    "mp-1194940": (6, -3, "left"),
    "mp-694937": (6, 2, "left"),
    "mp-578604": (6, 2, "left"),
}

for r in rows:
    x, y = float(r["v_lit"]), float(r["signed_err"])
    fam, grade, mp = r["family"], r["tier"], r["mp_id"]
    color = st.FAMILY_COLOR[fam]
    ax.scatter(x, y, s=26, marker=st.GRADE_MARKER[grade], zorder=3,
               facecolors=color, edgecolors=color, linewidths=0.9)
    dx, dy, ha = OFFSETS.get(mp, (6, 2, "left"))
    ax.annotate(st.SHORT_LABEL.get(mp, r["formula"]), (x, y),
                textcoords="offset points", xytext=(dx, dy), fontsize=6.3,
                ha=ha, color="0.15")

ax.set_ylim(err.min() - 0.22, err.max() + 0.22)

ax.annotate(f"$r = {r_committed:.3f}$", xy=(0.97, 0.90),
            xycoords="axes fraction", ha="right", fontsize=8.5)
ax.annotate("over-prediction", xy=(0.03, 0.97), xycoords="axes fraction",
            ha="left", va="top", fontsize=7, color="0.4", style="italic")
ax.annotate("under-prediction", xy=(0.03, 0.03), xycoords="axes fraction",
            ha="left", va="bottom", fontsize=7, color="0.4", style="italic")

ax.set_xlabel(r"Experimental average voltage $V_{\mathrm{lit}}$ (V)")
ax.set_ylabel(r"Signed error $V_{\mathrm{pred}}-V_{\mathrm{lit}}$ (V)")
ax.set_xlim(2.4, 4.8)

fig.savefig(st.FIGDIR / "fig2_residuals.pdf")
print(f"fig2_residuals.pdf written: n={len(rows)}, "
      f"r committed {r_committed} / recomputed {r_recomputed:.4f}")
