# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""Generate the paper's data tables as LaTeX fragments from committed artifacts.

Outputs (to ../tables/):
  t1_curated.tex      from na_wedge_diag/curated_na_cathodes.csv
  t2_metrics.tex      from na_wedge_diag/s3b_litexp_summary.json
  t3_family_bias.tex  from na_wedge_diag/step2_summary.json
  t5_baserate.tex     from na_wedge_diag/q2_collapse_summary.json +
                      gnome_debunk/gnome_screen_summary{,_structuredb}.json +
                      gnome_debunk/gnome_triage_probe_summary.json
  t6_ledger.tex       from qme.db (read-only)

Every numeric cell is read from an artifact; the only literals here are
LaTeX scaffolding and short display labels. t4_d1design.tex is hand-written
(design parameters quoted from the committed pre-registration, mapped in
CLAIMS_MAP S6.1-S6.2).
"""
import csv
import json
import re
import sqlite3

import qme_style as st

st.TABDIR.mkdir(exist_ok=True)


def ce(formula: str) -> str:
    return r"\ce{" + formula + "}"


# Short polymorph display labels keyed by (formula, mp_id); text only.
POLY_LABEL = {
    "mp-19226": "maricite",
    "mp-1203835": r"Pn2$_1$a",
    "mp-562796": r"ABW P2$_1$/n",
    "mp-683773": r"$\beta$ P6$_5$",
    "mp-1194940": "Pbcn",
    "mp-694937": "NVPF",
    "mp-578604": r"O3 R$\bar{3}$m",
}
POLY_LABEL_BY_FORMULA = {
    "Na2FeP2O7": r"P$\bar{1}$",
    "Na2Fe2(SO4)3": "alluaudite",
}


def t1_curated():
    with open(st.NWD / "curated_na_cathodes.csv") as f:
        body = [ln for ln in f if not ln.startswith("#")]
    rows = list(csv.DictReader(body))
    out = []
    out.append(r"\begin{ruledtabular}")
    out.append(r"\begin{tabular}{llllcld}")
    out.append(
        r"Compound & Polymorph & MP id & Family & Grade & DOI & "
        r"\multicolumn{1}{c}{$V_{\mathrm{lit}}$ (V)} \\"
    )
    out.append(r"\colrule")
    for r in rows:
        mp = r["mp_id"]
        poly = POLY_LABEL.get(mp) or POLY_LABEL_BY_FORMULA.get(r["formula"], "")
        marks = ""
        if r["self_audit_outcome"].strip().upper().startswith("EXCLUDED"):
            marks += r"\footnotemark[1]"
        if mp == "NO_MP_ENTRY":
            marks += r"\footnotemark[2]"
            mpcell = "n/a"
        else:
            mpcell = mp
        doi = r["citation_doi"]
        doicell = (r"\scriptsize\href{https://doi.org/" + doi + "}{" + doi + "}")
        fam = st.FAMILY_LABEL.get(r["family"], r["family"])
        out.append(
            f"{ce(r['formula'])}{marks} & {poly} & {mpcell} & {fam} & "
            f"{r['tier']} & {doicell} & {r['V_lit']} \\\\"
        )
    out.append(r"\end{tabular}")
    out.append(r"\end{ruledtabular}")
    out.append(r"\footnotetext[1]{Excluded from canonical metrics by the "
               r"operator audit (phase identity; Sec.~\ref{sec:resultsA2}).}")
    out.append(r"\footnotetext[2]{No MP structure exists; "
               r"literature-validated but not predictable by the screen.}")
    (st.TABDIR / "t1_curated.tex").write_text("\n".join(out) + "\n")
    return len(rows)


def t2_metrics():
    s = json.loads((st.NWD / "s3b_litexp_summary.json").read_text())
    order = ["held_out_all", "held_out_no_tierC", "phosphate_all",
             "phosphate_no_tierC"]
    label = {
        "held_out_all": "held-out, all grades",
        "held_out_no_tierC": r"held-out, A/B only\footnotemark[1]",
        "phosphate_all": "phosphate, all grades",
        "phosphate_no_tierC": "phosphate, A/B only",
    }
    out = []
    out.append(r"\begin{ruledtabular}")
    out.append(r"\begin{tabular}{lcddddd}")
    out.append(
        r"Set & $n$ & \multicolumn{1}{c}{raw MAE} & "
        r"\multicolumn{1}{c}{raw bias} & "
        r"\multicolumn{1}{c}{raw CI$_{95}$} & "
        r"\multicolumn{1}{c}{corr.\ MAE} & "
        r"\multicolumn{1}{c}{corr.\ CI$_{95}$} \\"
    )
    out.append(r"\colrule")
    for k in order:
        b = s["blocks"][k]
        out.append(
            f"{label[k]} & {b['n']} & {b['raw_MAE_V']:.3f} & "
            f"{b['raw_bias_V']:+.3f} & {b['raw_MAE_boot95_V'][1]:.3f} & "
            f"{b['loocv_corrected_MAE_V']:.3f} & "
            f"{b['loocv_corrected_MAE_boot95_V'][1]:.3f} \\\\"
        )
    out.append(r"\end{tabular}")
    out.append(r"\end{ruledtabular}")
    out.append(r"\footnotetext[1]{The canonical set after the operator-audit "
               r"exclusion. CI$_{95}$ columns give the upper edge of the 95\% "
               r"bootstrap interval on the MAE; the corrected upper edge of "
               r"this row is the pre-registered primary metric. All values in "
               r"volts.}")
    (st.TABDIR / "t2_metrics.tex").write_text("\n".join(out) + "\n")
    return s["blocks"]["held_out_no_tierC"]["loocv_corrected_MAE_boot95_V"][1]


def t3_family_bias():
    s = json.loads((st.NWD / "step2_summary.json").read_text())
    fams = s["per_family_diagnostic"]
    order = ["polyanionic_phosphate", "layered_oxide", "other", "NASICON"]
    disp = {
        "polyanionic_phosphate": "polyanionic phosphate",
        "layered_oxide": "layered oxide",
        "other": r"other (mixed-anion, fluorides)\footnotemark[1]",
        "NASICON": "NASICON",
    }
    out = []
    out.append(r"\begin{ruledtabular}")
    out.append(r"\begin{tabular}{lcdd}")
    out.append(r"Family & $n$ & \multicolumn{1}{c}{bias (V)} & "
               r"\multicolumn{1}{c}{MAE (V)} \\")
    out.append(r"\colrule")
    for k in order:
        d = fams[k]
        out.append(f"{disp[k]} & {d['n']} & {d['bias']:+.4f} & "
                   f"{d['mae']:.4f} \\\\")
    out.append(r"\end{tabular}")
    out.append(r"\end{ruledtabular}")
    out.append(r"\footnotetext[1]{Mostly carbonate-polyanionic "
               r"(P/As/Si--C--O) and halide chemistries, the least "
               r"represented in the training corpus.}")
    (st.TABDIR / "t3_family_bias.tex").write_text("\n".join(out) + "\n")
    return s["failure_modes"]["F1_observed_spread_V"]


def t5_baserate():
    q2 = json.loads((st.NWD / "q2_collapse_summary.json").read_text())
    g1 = json.loads((st.GNOME / "gnome_screen_summary.json").read_text())
    g2 = json.loads(
        (st.GNOME / "gnome_screen_summary_structuredb.json").read_text())
    g3 = json.loads(
        (st.GNOME / "gnome_triage_probe_summary.json").read_text())

    # Hand-audited true positives are recorded in the structuredb note string.
    m = re.search(r"(\d+)/5 verified TP", g2["title_only_baseline"]["note"])
    assert m, "hand-audit count not found in committed artifact"
    tp = int(m.group(1))
    floor_pct = 100.0 * tp / g1["n_sample"]

    funnel = g3["funnel_narrowing_4a"]
    by = q2["by_path"]

    rows = [
        (r"\multicolumn{2}{l}{\itshape Targeted earth-abundant Na space "
         r"(substitution generator)}", None),
        ("enumerated compositions", f"{q2['n_distinct_enumerated']}"),
        ("SMACT-valid", f"{q2['n_smact_valid_screened']}"),
        (r"flagged already-published (lower bound)\footnotemark[1]",
         f"{q2['flagged_debunkable_as_known']} ({q2['flagged_pct']:.1f}\\%)"),
        (r"\quad via structural family", f"{by['structural_family']}"),
        (r"\quad via COD exact composition", f"{by['COD_exact_structure']}"),
        (r"\quad via named literature citation", f"{by['literature_named']}"),
        ("survivors (absent within coverage)",
         f"{q2['survivors_not_debunkable']}"),
        (r"\multicolumn{2}{l}{\itshape GNoME stable-materials release "
         r"(pinned uniform sample)}", None),
        ("population / sample",
         f"{g1['n_total_population']:,} / {g1['n_sample']}"),
        ("flagged by title-level screen",
         f"{g1['flagged_prior_art']} ({g1['flagged_pct']:.1f}\\%)"),
        (r"hand-verified true positives\footnotemark[2]",
         f"{tp}/{g1['flagged_prior_art']} (floor {floor_pct:.1f}\\%)"),
        ("COD exact-composition matches",
         f"{g2['structure_db_cod']['exact_cod_matches']}/{g1['n_sample']}"),
        ("prior-art-absent carried to funnel", f"{funnel['N_input']}"),
        (r"\quad after SMACT validity", f"{funnel['after_smact']}"),
        (r"\quad after stability screen",
         f"{funnel['after_oracle_stability']}"),
        (r"\quad after polaron screen (survivors)",
         f"{funnel['after_polaron_nonblocking']} "
         f"({funnel['survivors_pct_of_input']:.1f}\\%)"),
        (r"stability disputes vs GNoME label\footnotemark[3]",
         f"{g3['echo_test_4c']['oracle_dispute_rate_pct']:.1f}\\%"),
    ]

    out = []
    out.append(r"\begin{ruledtabular}")
    out.append(r"\begin{tabular}{lr}")
    out.append(r"Quantity & Value \\")
    out.append(r"\colrule")
    for left, right in rows:
        if right is None:
            out.append(left + r" \\")
        else:
            out.append(f"{left} & {right} \\\\")
    out.append(r"\end{tabular}")
    out.append(r"\end{ruledtabular}")
    out.append(r"\footnotetext[1]{The prior-art layer only downgrades and "
               r"two of its sources are stubs; flagged rates are lower "
               r"bounds. Paths overlap.}")
    out.append(r"\footnotetext[2]{Hand audit of every flagged hit.}")
    out.append(r"\footnotetext[3]{Disagreement rate between the borrowed "
               r"stability model and the GNoME label; a correctness claim "
               r"for neither.}")
    (st.TABDIR / "t5_baserate.tex").write_text("\n".join(out) + "\n")
    return floor_pct


def t6_ledger():
    con = sqlite3.connect(f"file:{st.DB}?mode=ro", uri=True)
    cur = con.execute(
        """
        SELECT vr.id, c.formula, vr.voltage_computed, vr.anchor_weight,
               (SELECT GROUP_CONCAT(DISTINCT d.u_provenance)
                  FROM dft_runs d
                 WHERE d.candidate_id = vr.candidate_id
                   AND d.u_provenance IS NOT NULL
                   AND d.u_provenance != '') AS uprov,
               (SELECT GROUP_CONCAT(DISTINCT d.backend)
                  FROM dft_runs d
                 WHERE d.candidate_id = vr.candidate_id) AS backends
          FROM verified_results vr
          JOIN candidates c ON c.id = vr.candidate_id
         ORDER BY vr.id
        """
    )
    rows = cur.fetchall()
    con.close()

    def role(formula, w):
        if w and w > 0:
            return "anchor"
        if formula == "Na3V2(PO4)3":
            return "touchpoint"
        return "computed-only"

    BACKEND_LABEL = {"runpod": "cloud", "local_macmini": "local"}
    UPROV_LABEL = {"literature_standard": "lit.", "empirical_fit": "emp."}

    def backend_cell(backends):
        kinds = sorted({BACKEND_LABEL.get(x, x)
                        for x in (backends or "").split(",")})
        return "mixed" if len(kinds) > 1 else kinds[0]

    out = []
    out.append(r"\begin{ruledtabular}")
    out.append(r"\begin{tabular}{ldllc}")
    out.append(r"Compound & \multicolumn{1}{c}{$V$ (V)} & Role & "
               r"$U$ prov. & Backend \\")
    out.append(r"\colrule")
    for (_id, formula, v, w, uprov, backends) in rows:
        up = "/".join(UPROV_LABEL.get(x, x) for x in (uprov or "").split(","))
        be = backend_cell(backends)
        out.append(f"{ce(formula)} & {v} & {role(formula, w)} & "
                   f"{up} & {be} \\\\")
    out.append(r"\end{tabular}")
    out.append(r"\end{ruledtabular}")
    (st.TABDIR / "t6_ledger.tex").write_text("\n".join(out) + "\n")
    return len(rows)


if __name__ == "__main__":
    n1 = t1_curated()
    primary = t2_metrics()
    spread = t3_family_bias()
    floor = t5_baserate()
    n6 = t6_ledger()
    print(f"tables written: t1 ({n1} rows), t2 (primary metric "
          f"{primary:.4f} V), t3 (F1 spread {spread} V), "
          f"t5 (GNoME floor {floor:.1f}%), t6 ({n6} ledger rows)")
