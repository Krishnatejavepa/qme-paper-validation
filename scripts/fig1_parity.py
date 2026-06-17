# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""F1, parity plot: predicted vs experimental average voltage.

Reads the committed per-row results (s3b_litexp_results.csv) and the curated
set (curated_na_cathodes.csv, for the operator-audit exclusion flag). The
maricite row is drawn as an open marker: excluded from canonical metrics for
phase identity. No per-point error bars are drawn because no committed
per-row uncertainty artifact exists (deviation from the F1 spec, logged for
HALT-2).
"""
import csv

import matplotlib.pyplot as plt

import qme_style as st

st.apply()

rows = []
with open(st.NWD / "s3b_litexp_results.csv") as f:
    for r in csv.DictReader(f):
        rows.append(r)

excluded = set()
with open(st.NWD / "curated_na_cathodes.csv") as f:
    body = [ln for ln in f if not ln.startswith("#")]
for r in csv.DictReader(body):
    if r["self_audit_outcome"].strip().upper().startswith("EXCLUDED"):
        excluded.add(r["mp_id"])

fig, ax = plt.subplots(figsize=(st.SINGLE_COL, st.SINGLE_COL))

lo, hi = 2.4, 4.8
ax.plot([lo, hi], [lo, hi], ls="--", lw=0.7, color="0.55", zorder=1)

# Per-point label offsets (dx pt, dy pt, ha) tuned against collisions.
OFFSETS = {
    "mp-19226": (5, 2, "left"),
    "mp-1203835": (4, -10, "left"),
    "mp-562796": (-6, -10, "right"),
    "mp-683773": (0, 7, "center"),
    "mp-1194940": (5, -3, "left"),
    "mp-694937": (-5, -11, "right"),
    "mp-578604": (5, 2, "left"),
}

for r in rows:
    x, y = float(r["v_lit"]), float(r["v_pred"])
    fam, grade, mp = r["family"], r["tier"], r["mp_id"]
    color = st.FAMILY_COLOR[fam]
    marker = st.GRADE_MARKER[grade]
    is_excl = mp in excluded
    ax.scatter(
        x, y, s=26, marker=marker, zorder=3,
        facecolors="none" if is_excl else color,
        edgecolors=color, linewidths=0.9,
    )
    label = st.SHORT_LABEL.get(mp, r["formula"])
    dx, dy, ha = OFFSETS.get(mp, (4, 4, "left"))
    ax.annotate(
        label + (" (excl.)" if is_excl else ""),
        (x, y), textcoords="offset points", xytext=(dx, dy),
        fontsize=6.3, ha=ha, color="0.15",
    )

ax.set_xlim(lo, hi)
ax.set_ylim(lo, hi)
ax.set_aspect("equal")
ax.set_xlabel(r"Experimental average voltage $V_{\mathrm{lit}}$ (V)")
ax.set_ylabel(r"Predicted average voltage $V_{\mathrm{pred}}$ (V)")

fam_handles = [
    plt.Line2D([], [], ls="", marker="o", color=st.FAMILY_COLOR[f],
               label=st.FAMILY_LABEL[f])
    for f in ("polyanionic_phosphate", "polyanionic_fluorophosphate",
              "layered_oxide")
]
grade_handles = [
    plt.Line2D([], [], ls="", marker=m, mfc="none", mec="0.25",
               label=f"grade {g}")
    for g, m in st.GRADE_MARKER.items()
]
leg1 = ax.legend(handles=fam_handles, loc="upper left", handletextpad=0.1,
                 borderaxespad=0.2)
ax.add_artist(leg1)
ax.legend(handles=grade_handles, loc="lower right", handletextpad=0.1,
          borderaxespad=0.2)

fig.savefig(st.FIGDIR / "fig1_parity.pdf")
print("fig1_parity.pdf written:", len(rows), "points,",
      len(excluded), "excluded row(s) drawn open")
