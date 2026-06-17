# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""F3, three-way decomposition for the polymorph-resolved NaCoPO4 rows.

Reads three_way_decomposition from s3b_litexp_summary.json: model prediction,
MP computed reference, and quote-anchored experimental value per polymorph,
with the MP-minus-experiment offset annotated from the artifact.
"""
import json
from decimal import Decimal, ROUND_HALF_UP

import matplotlib.pyplot as plt

import qme_style as st


def r3(v: float) -> str:
    """Round half away from zero at 3 decimals, matching the committed
    report's rounding (-0.5375 -> -0.538), signed."""
    q = Decimal(str(v)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return f"{q:+}"

st.apply()

summary = json.loads((st.NWD / "s3b_litexp_summary.json").read_text())
rows = summary["three_way_decomposition"]

fig, ax = plt.subplots(figsize=(st.SINGLE_COL, st.SINGLE_COL * 0.62))

KIND = [
    ("v_pred", "model $V_{\\mathrm{pred}}$", st.OKABE_ITO["vermillion"], "o"),
    ("v_mp", "MP reference $V_{\\mathrm{MP}}$", st.OKABE_ITO["blue"], "D"),
    ("v_lit", "experiment $V_{\\mathrm{lit}}$", st.OKABE_ITO["black"], "*"),
]

ypos = [1.0, 0.0]
for y, d in zip(ypos, rows):
    vals = [d[k] for k, _, _, _ in KIND]
    ax.plot([min(vals), max(vals)], [y, y], lw=0.9, color="0.7", zorder=1)
    for (k, _, color, marker) in KIND:
        ax.scatter(d[k], y, s=42 if marker == "*" else 24, marker=marker,
                   color=color, zorder=3)
    # MP-vs-experiment bracket, value from the artifact
    ax.annotate(
        f"$V_{{\\mathrm{{MP}}}}-V_{{\\mathrm{{lit}}}} = "
        f"{r3(d['mp_minus_lit'])}$ V",
        xy=((d["v_mp"] + d["v_lit"]) / 2, y + 0.18), ha="center",
        fontsize=6.8, color="0.25",
    )

labels = []
for d in rows:
    poly = "ABW" if "ABW" in d["polymorph"] else r"$\beta$"
    labels.append(f"NaCoPO$_4$ ({poly})")
ax.set_yticks(ypos, labels)
ax.set_ylim(-0.45, 2.05)
ax.margins(x=0.07)
ax.set_xlabel("Average voltage (V)")

handles = [
    plt.Line2D([], [], ls="", marker=m, color=c, label=lab,
               markersize=7 if m == "*" else 5)
    for _, lab, c, m in KIND
]
ax.legend(handles=handles, loc="upper left", handletextpad=0.1,
          borderaxespad=0.2)

fig.savefig(st.FIGDIR / "fig3_decomposition.pdf")
print("fig3_decomposition.pdf written:", [d["mp_id"] for d in rows])
