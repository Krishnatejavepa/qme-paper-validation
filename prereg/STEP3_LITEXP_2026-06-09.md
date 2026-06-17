# STEP3_LITEXP, Phase B Step 3 (2026-06-09): **HALTED at F5**

> Companion to `preregistration_2026-06-08.md` (locked tiers + failure modes
> incl. NEW F5 "uncitable subset" stop-condition) and
> `STEP2_BIAS_CORRECTED_2026-06-09.md` (identified `polyanionic_phosphate`
> n=26 as the recoverable family after F1 invalidated the global verdict).

## Headers

| Field | Value |
|---|---|
| Pre-registration commit SHA | `bd254c2` (tiers + F1-F4 + F5 locked) |
| Step 2 commit SHA | `ad780bb` (family-restricted to polyanionic_phosphate) |
| Step 3 branch | `phase-b/step3-litexp-2026-06-09` (off `phase-b/step1-step2-2026-06-09`) |
| Subset attempted | all 26 polyanionic_phosphate compounds from Step 2 (`step2_per_compound.csv` filtered family == 'polyanionic_phosphate') |
| Out-of-family disambiguation candidates identified | 9 layered_oxide + 1 NASICON (10 total), **NOT curated due to F5 firing on the primary subset** |
| **n_polyanionic_phosphate_with_extractable_V_lit** | **0 / 26 (0%)** |
| **n_polyanionic_phosphate with literature mention but no extractable V_avg** | **3 / 26** (NaCoPO4 ×2 polymorphs, NaMnPO4 maricite) |
| n_unverified_dropped (per S3.2 spec) | 26 / 26 (100%) |
| **F5 status** | **FIRED HARD: 100% uncitable for extractable V_avg, well above the 50% STOP threshold** |
| Per-compound curation log | `na_wedge_diag/step3_curation_log.csv` (committed alongside this report) |

---

## Why F5 fired, the OOS test set is mostly computational, not synthesized

The 26 polyanionic_phosphate compounds in our OOS set were drawn from
`na_ion_candidates.csv`, which itself comes from the **Materials Project Battery
API** (`average_voltage` column = MP's computed Na intercalation potential).
That API ranks any composition with a computable Na chemical potential, **not
just compositions that have been experimentally synthesized as Na cathodes.**

Pattern observed across all 26 attempts (full per-compound log in
`step3_curation_log.csv`):

| Category | Count | Examples |
|---|---:|---|
| Published as Na-ion cathode in primary literature, V_avg in abstracts | **0** |, |
| Published as Na-ion cathode, V_avg only inside paywalled full text | 3 | NaCoPO4 (mp-562796, mp-683773 polymorphs); NaMnPO4 maricite (mp-1210501) |
| Structural / crystallography literature only (1980s-1990s solid-state chemistry); no Na-cathode electrochemistry published | 3 | NaMo2P3O13 polymorphs (mp-557638, mp-559036), Mo3P3O13 (mp-1012678), ζ-NaMo2P3O13 was reported in *J. Solid State Chem.* (1990) as a structure, not a battery material |
| Related but not identical compound published as Na cathode (NOT a substitute) | 2 | Mo2P2O11 (3.0 V vs Na, *Energy Fuels* 2023) is reported as a Mo-oxypyrophosphate cathode, but it's **not** Mo3P3O13 or MoP2O7 in our OOS set |
| No Na-ion cathode publication of any form | **18** | Cu(PO3)3, Cu9(PO4)8, Cu2P2O7, Fe(PO3)3, Mn6P7O24, Co2P3O10, Ca9Co(PO4)7 (whitlockite), Ti3Fe(PO4)6, all V phosphate variants in this set (V2P2O9, VP2O7, VPO5, V(PO4)2, V3P2O13), all remaining Mo phosphate variants (Mo(PO4)2, Mo4P5O24) |
| **Citable per S3.2 strict spec** (DOI + author + year + extractable V_avg with redox couple) | **0** |, |

The strict S3.2 requirement was:

> REQUIRED: full citation (authors, year, journal, DOI if available)
> REQUIRED: V_avg with explicit voltage window OR single-plateau voltage with
> redox couple identified
> ...
> Hard rule: NO ROW WITHOUT A TRACEABLE CITATION.

The 3 compounds with literature mentions (NaCoPO4 polymorphs + NaMnPO4
maricite) fail the **extractable V_avg** part: the published abstracts
describe these as cathode materials but report cycling windows (e.g.
"2.0-4.0 V") rather than a single average voltage with the redox couple
attribution. Without paywalled full-text access I cannot honestly extract a
single V_avg figure for any of them. **Searching for a flattering value in
adjacent papers, or inferring V_avg from window midpoints, would be exactly
the GNoME-style fabrication failure mode that the user's spec explicitly
prohibited.**

Compounds with no literature at all (18 of 26 = 69%) can't be cited under any
interpretation.

**F5 STOP condition:** "if >50% of polyanionic_phosphate compounds in S3.1
cannot be cited from primary literature, the subset is not defensibly
'experimental.' STOP and report, do not invent or estimate citations to hit
the count."

**100% > 50%. Step 3 stops here.**

---

## What this means for the original Step 3 hypotheses

Step 3 was designed to disambiguate the +0.20 V polyanionic_phosphate GNN
bias via the three-way decomposition

```
(V_pred − V_lit) = (V_pred − V_MP) + (V_MP − V_lit)
```

so that we could distinguish:
- a real GNN bias on phosphate chemistry (V_MP − V_lit ≈ 0)
- an MP-PBE+U-vs-experiment offset that QME's predictor inherited
  (V_MP − V_lit ≈ +0.20 V → headline bias ≈ 0 V)
- a worst-case compounding (V_MP − V_lit ≈ −0.20 V → headline bias ≈ +0.40 V)

**With F5 fired, none of these can be computed.** `V_lit` doesn't exist for
the 26-compound polyanionic_phosphate OOS subset. The disambiguation is not
possible against this compound set.

This does NOT invalidate Step 2's bias-corrected MAE = 0.6610 V on LOFO or
the +0.20 V polyanionic_phosphate-within-family bias, those numbers stand
because they compare (V_pred) to (V_MP) and both exist for all 74 rows. What
fails is **the upgrade to (V_pred vs experiment)** on this subset.

---

## MP-vs-experiment offset finding (NOT computable; flagged for separate work)

The pre-spec asked Step 3 to flag the MP-PBE+U-vs-experiment offset on
polyanionic_phosphate as **independently consequential** for QME's DFT
pipeline (since QME uses PBE+U for its own anchors). **That flag stands a
priori**, even without Step 3 evidence:

- The subfolder `qme_battery_loop/CLAUDE.md` "Current Status" row records
  Na₃V₂(PO₄)₃: **QME PBE+U → 2.90 V vs ≈3.4 V experiment**, a ~0.5 V
  under-prediction (MP-PBE+U-vs-experiment offset of roughly the same sign).
  This compound is **NOT in our OOS set** and remains out of scope for Step
  3 per the binding caveat from Step 2, but it's pre-existing evidence
  that the MP-PBE+U-vs-experiment offset on Na vanadium phosphates is
  non-zero and ~0.5 V.
- This is sufficient to warrant a **separate follow-up specifically auditing
  the MP-PBE+U-vs-experiment systematic offset across known Na cathodes**,
  using the curated set we'd need to assemble anyway for a redesigned Step 3
  (see Recommendation below).

---

## Voltage-dependence check (NOT computable)

Cannot be performed without V_lit. The Step 2 per-compound CSV already
shows the residuals are not flat in V_pred (see
`step2_per_compound.csv` sorted by `v_pred`), but without literature
references we can't disentangle "model worse at higher V" from "MP-computed
V_avg has different systematic offsets at high V."

---

## Verdict against pre-registered tiers, **NOT ISSUED**

F5 prevents a literature-experimental tier verdict on this compound set.
The pre-registered Step 2 verdict, **F1-invalidated, family-restricted to
polyanionic_phosphate where the within-family raw MAE is 0.3753 V and the
within-family raw bias is +0.2022 V**, remains the current best
characterization, with the explicit acknowledgement that those numbers are
against MP-computed reference voltages, not experiment.

---

## Out-of-family disambiguation, NOT performed

S3.7 (5-10 layered_oxide / NASICON-fluoride / sulfate compounds for
disambiguating whether MP-vs-experiment offsets are family-specific) was not
attempted: the same F5 problem would apply to the out-of-family candidates
in our OOS set (which are equally MP-API-derived, not experimentally
curated). Spending search effort on compounds we cannot then compare against
the primary polyanionic_phosphate result is wasted.

The 10 disambiguation candidates that WERE identified for the record:

| Family | mp_id | Formula | V_pred | V_MP_ref |
|---|---|---|---|---|
| NASICON | mp-541674 | Na0-1Mo2(PO4)3 | 3.592 | 3.009 |
| layered_oxide | mp-867515 | Na0-1CoO2 | 3.969 | 3.009 |
| layered_oxide | mp-1101719 | Na0-1Cr3O8 | 4.348 | 4.338 |
| layered_oxide | mp-18999 | Na0-1Mn7O12 | 3.315 | 3.508 |
| layered_oxide | mp-1173562 | Na0-1V3Fe2CuO12 | 3.370 | 4.169 |
| layered_oxide | mp-1176383 | Na0-1.5V12O29 | 3.711 | 3.771 |
| layered_oxide | mp-761084 | Na0-1.25V9O22 | 3.739 | 3.442 |
| layered_oxide | mp-778594 | Na0-0.67V2O5 | 3.791 | 3.212 |
| layered_oxide | mp-560778 | Na0-1.29V2O5 | 3.464 | 3.211 |
| layered_oxide | mp-558048 | Na0-1V(GeO3)2 | 3.817 | 3.157 |

Most are obscure mixed-TM oxides with the same MP-derivation issue. Only
NaCoO2 (mp-867515) is a publicly-known Na cathode; the others are MP-only.

---

## Failure-mode summary (pre-registered)

| Mode | Status |
|---|---|
| F1 (family-bias spread > 0.15 V) | **FIRED in Step 2**, invalidates global tier; verdict family-restricted |
| F2 (in-sample contamination) | not applicable (no analysis ran) |
| F3 (N < 20) | not applicable (no analysis ran) |
| F4 (mixed-sign family biases) | not applicable (no analysis ran) |
| **F5 (>50% uncitable in polyanionic_phosphate)** | **FIRED HARD: 100% uncitable, STOP-condition** |

---

## Honest takeaways

1. **The 74-compound OOS test set is not a curated experimental dataset.**
   It is an MP Battery API-derived list dominated by computational entries.
   The Phase B PRE-AUDIT's `q1_oos.py` artefact rigorously held compounds
   out of the GNN's *training graphs*, but that's a different orthogonality
   than holding compounds out of the *known-experimentally-synthesized*
   universe. The two are conflated in the existing OOS design.
2. **Step 2's polyanionic_phosphate within-family numbers (raw MAE 0.3753 V,
   raw bias +0.2022 V) remain valid**, they measure GNN-vs-MP-computed
   reference, which is what the data actually supports. The Phase B PRE-AUDIT
   identified this caveat (§P1.2) before Step 3 began; F5 sharpens it from
   "MP-computed is a less-rigorous proxy" to "the OOS subset itself has very
   little experimental ground truth published."
3. **A working Step 3 requires a different, curated compound set.** That
   set has to be built from KNOWN published Na cathodes (NaCoPO4 polymorphs,
   NaMnPO4 maricite, NaFePO4, Na4Fe3(PO4)2(P2O7), Na2FePO4F,
   Na2FeP2O7, NaFeSO4F, ...), with the GNN predictions then *generated* on
   those compounds (new MP-fetch + new `predict_from_structure` calls, not
   re-using the OOS table). This is a redesign, not a continuation.
4. **The MP-PBE+U-vs-experiment systematic offset still deserves separate
   investigation** in QME's own DFT pipeline, independent of Step 3
   succeeding, because the pre-existing Na₃V₂(PO₄)₃ DFT result (≈0.5 V
   under-prediction vs experiment) is suggestive evidence of a systematic
   offset that affects QME's anchors directly.

---

## Na₃V₂(PO₄)₃ scope (mandatory caveat)

Na₃V₂(PO₄)₃ is **NOT** in the polyanionic_phosphate subset (not in the OOS
74). The well-known ~0.5 V under-prediction by QME's PBE+U DFT on this
compound is referenced above only as **independent prior evidence** that
the MP-PBE+U-vs-experiment offset is non-zero on Na vanadium phosphates -
not as a substitute for the Step 3 disambiguation. Its DFT result remains
out of scope of this Step 3 analysis.

---

## Recommendation (one line, per F5 firing)

**Stop, redesign Step 3 around a curated KNOWN-experimental Na cathode set
(8-15 compounds), then either re-run literature curation against that set or
skip directly to Step 4 (MACE-MP-0 comparator) on the same curated set.**

The Step 2 verdict (family-restricted to polyanionic_phosphate;
within-family raw MAE 0.3753 V; bias-corrected story requires within-family
validation) stands as the current state. The next operator decision is:

- **(α)** Curate a small known-experimental Na cathode set (8-15 compounds)
  with citations from primary literature, fetch MP structures, run
  `predict_from_structure` on each, compute V_pred vs V_lit. Step 3 redo. ~4-8 h
  including focused literature reading.
- **(β)** Skip Step 3 entirely; proceed to Step 4 (MACE-MP-0 comparator) on
  the existing 74-compound OOS set, comparing MACE-derived V_avg to GNN-
  derived V_avg both against V_MP. This still cannot validate against
  experiment, but it does test whether the +0.20 V GNN bias on
  polyanionic_phosphate is GNN-specific or shared with another energy
  surrogate. ~2-4 h compute.
- **(γ)** Both (α) and (β) in sequence, (β) first because it's cheaper, then
  (α) once the MACE comparator clarifies what (α)'s reference-data
  replacement needs to test.
- **(δ)** Stop; publish the Step 1 + Step 2 result as-is with the F5 finding
  as part of the methodology paper (the "OOS-vs-experiment gap on this
  dataset" finding is itself publishable as a methodology insight).

Operator decides. Do not execute autonomously.
