# D1 OFFSET AUDIT, PRE-REGISTRATION (committed BEFORE any result exists)

**Purpose (gate G1).** Measure the offset δ = V_QME(PBE+U) − V_experiment on known Li-ion
couples to determine whether QME's bench is *calibratable*, the single gate that decides
whether absolute-voltage language survives anywhere in QME.

**Decision rule (pre-committed, no post-hoc adjustment):**
- **PASS**, sd(δ) < 0.15 V across the offset points → the scale is calibratable per
  chemistry family; publish voltages with the calibrated offset and error bars.
- **FAIL**, sd(δ) ≥ 0.3 V → absolute-voltage claims are retired everywhere
  (ranking-only language); hp.x ab-initio U (D9) and beyond-PBE+U methods become the path.
- **GRAY ZONE**, 0.15 ≤ sd < 0.3 V → operator decision, documented at sync time.

**Offset points.** Core n=3: (1) LiCoO₂, already computed 4.120 V (existing anchor);
(2) LiFePO₄/FePO₄; (3) Li₂FeP₂O₇/LiFeP₂O₇. Stretch 4th point: LiMn₂O₄/λ-MnO₂ -
**pre-registered as STRETCH-COMPOUND**: if either Mn half fails to converge in the
registered spin manifold, the verdict is issued on the n=3 core alone and the Mn point is
reported as excluded (this exclusion path is pre-committed here, not decided after results).

## Experimental references (pre-registered targets)

| Couple | V_exp (V) | Source |
|---|---|---|
| LiCoO₂ → Li₀.₅CoO₂ | 4.0 (3.9-4.1 window) | standard plateau; existing QME benchmark |
| LiFePO₄ → FePO₄ | 3.45 | Padhi, Nanjundaswamy & Goodenough, J. Electrochem. Soc. 144, 1188 (1997) |
| Li₂FeP₂O₇ → LiFeP₂O₇ | 3.5 | Nishimura, Nakamura, Natsui & Yamada, JACS 132, 13596 (2010) |
| LiMn₂O₄ → λ-MnO₂ | 4.05 (avg of ~3.95/~4.15 plateaus) | Thackeray et al., Mater. Res. Bull. 18, 461 (1983); Ohzuku et al., JES 137, 769 (1990) |

## The six runs (inputs staged by `qme_battery_loop/tasks/d1_stage_inputs.py`)

| Job | Cell | nat | n_Li | Structure source |
|---|---|---|---|---|
| d1_lifepo4_li | LiFePO₄ olivine, conventional | 28 | 4 | MP mp-19017 (e_hull 0.0000) |
| d1_fepo4_de | FePO₄ heterosite (topotactic Li removal from the same cell) | 24 | 0 | derived |
| d1_li2fep2o7_li | Li₂FeP₂O₇, conventional (4 f.u.) | 48 | 8 | MP mp-779056 (e_hull 0.0044) |
| d1_lifep2o7_li | LiFeP₂O₇, QME canonical 4-f.u. cell, RE-RUN on QE 7.3.1 | 44 | 4 | `candidates.structure_json` (id 5) |
| d1_limn2o4_li | LiMn₂O₄ spinel, primitive (2 f.u.), STRETCH | 14 | 2 | MP mp-1272804 (e_hull 0.0000) |
| d1_lmno2_de | λ-MnO₂ (topotactic Li removal from the same cell), STRETCH | 12 | 0 | derived |

All n_Li values above were **counted from the actual staged cells** (not inferred from
formulas) and are re-asserted by hard checks in the analysis script before any voltage is
computed.

## Magnetics, pre-registered BEFORE submission

FM (ferromagnetic alignment) is the registered convention for all runs, the established
MP / Wang-2006 GGA+U voltage convention, with free vc-relax (ibrav=0, no symmetry
constraint), so Jahn-Teller distortion is allowed wherever the electronics want it.

| Run | Registered manifold | Expected converged total |mag| |
|---|---|---|
| d1_lifepo4_li | 4×Fe²⁺ HS (d⁶, 4 μB) FM | 16.0 μB |
| d1_fepo4_de | 4×Fe³⁺ HS (d⁵, 5 μB) FM | 20.0 μB |
| d1_li2fep2o7_li | 4×Fe²⁺ HS FM | 16.0 μB |
| d1_lifep2o7_li | 4×Fe³⁺ HS FM | 20.0 μB |
| d1_limn2o4_li | FM, mixed-valence 2×Mn³⁺ HS (d⁴, 4 μB) + 2×Mn⁴⁺ (d³, 3 μB); **JT allowance: free vc-relax**, the two Mn classes may differentiate bond lengths | 14.0 μB |
| d1_lmno2_de | 4×Mn⁴⁺ (d³) FM | 12.0 μB |

**LiMn₂O₄ caveat (the reason it is the stretch compound):** the true low-T ground state is
charge-ordered/AFM orthorhombic (Rodríguez-Carvajal et al., PRL 81, 4660 (1998)); FM cubic
spinel is the standard computational convention for the room-temperature average voltage
(Wang & Ceder GGA+U convention) but contributes a documented model-choice uncertainty of
order tens of meV/f.u. Spin-consistency rule (pre-committed): a pair half that converges
outside its registered manifold (e.g. spin-sloshed non-integer magnetization à la
Na₃Fe₂(PO₄)₃) excludes that offset point from the gate statistic.

## Run parameters (identical across all six; identical to the anchor scale)

QE 7.3.1 local (`local_macmini`) · vc-relax · ecutwfc 50 Ry / ecutrho 200 Ry · gaussian
smearing 0.01 Ry · `HUBBARD {ortho-atomic}` after K_POINTS · **U: Fe-3d 5.30, Mn-3d 3.90**
(literature_standard; Co 3.4 applies only to the existing LiCoO₂ point) · mixing local-TF ·
pinned pseudos: `li_pbe_v1.4.uspp.F.UPF`, `Fe.pbe-spn-kjpaw_psl.0.2.1.UPF`,
`P.pbe-n-rrkjus_psl.1.0.0.UPF`, `O.pbe-n-kjpaw_psl.0.1.UPF`, `mn_pbe_v1.5.uspp.F.UPF` ·
μ_Li = −14.4725646547 Ry (in-DB BCC reference run).

## Voltage formulas (explicit n_Li bookkeeping)

Ry→eV = 13.605693122994. μ = μ_Li above.

- **Pair A (same cell, Δn=4):** V = −[E(d1_lifepo4_li) − E(d1_fepo4_de) − 4μ]·Ry→eV / 4
- **Pair B (different cells, both 4 f.u., Δn=1 per f.u.):**
  V = −[E(d1_li2fep2o7_li)/4 − E(d1_lifep2o7_li)/4 − 1·μ]·Ry→eV / 1
  (hard-asserted: nat 48 & 44, n_Li 8 & 4 → 4 f.u. each)
- **Pair C (same cell, Δn=2):** V = −[E(d1_limn2o4_li) − E(d1_lmno2_de) − 2μ]·Ry→eV / 2

Energies are the `Final enthalpy` after `bfgs converged` (never the post-convergence
`! total energy`), per the established parsing rule.

## Execution order (lowest-attention first: phosphates, then Mn last)

1. d1_lifepo4_li → 2. d1_fepo4_de → 3. d1_li2fep2o7_li → 4. d1_lifep2o7_li →
5. d1_limn2o4_li → 6. d1_lmno2_de, sequential, one `pw.x` at a time, on the
`~/.qme_loop/qme_local_scheduler.py` queue (results land in `runpod_data/results.json`,
then human-gated sync to `qme.db`).

Analysis: `qme_battery_loop/tasks/d1_offset_analysis.py` (committed as a stub alongside
this document, before results exist). Scoping note: the pre-check verdict on this audit
design was PARTIAL (inherited from the 2026-06-10 review); the Li₂FeP₂O₇ endpoints are
relaxed in their own equilibrium cells (the thermodynamically correct two-phase treatment),
and the LiFeP₂O₇ re-run replaces the RunPod-era energy with a same-machine QE 7.3.1 value
so pair B sits entirely on the local scale.
