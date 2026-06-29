# qme-paper-validation

Code and data for the paper "Computational references are not experiments:
pre-registered validation of machine-learned sodium-cathode voltages"
(K. T. Vepa). arXiv: https://arxiv.org/abs/2606.23725 (V2 announced soon)

## Summary

Machine-learning voltage screens for battery cathodes are usually trained and
checked against computed reference voltages, for example PBE+U values from public
databases, and those references carry their own systematic error. This paper runs
our screening stack (a graph-network voltage model, a prior-art filter, and a
local PBE+U bench) against experiment-anchored literature voltages for known
sodium cathodes, under a protocol whose thresholds, primary metric, and failure
modes were registered before the analysis was run.

The screen does not pass. On the audited canonical set (n=6) the raw held-out
error is 0.67 V and the pre-registered conservative metric is 1.09 V, and the
residual depends strongly on voltage (r = -0.94), so an additive calibration
cannot fix it. On the two compounds where prediction, database reference, and
experiment can all be compared, the database PBE+U reference itself sits about
0.54 V below experiment, so the reference, not the model, carries most of the
error. A pre-registered calibration audit of our own PBE+U bench then fails the
same kind of gate (the four benchmark-couple offsets have a standard deviation of
0.31 V, above the 0.30 V bar), so absolute-voltage claims are retired from our own
ledger in favor of ranking-only language.

This repository holds the committed inputs and code behind those numbers so the
figures and tables can be regenerated from a clean checkout.

## Layout

- `paper/`: manuscript source (`paper.tex`, `paper.bbl`), the compiled PDF,
  `refs.bib`, and the figures and tables the paper includes.
- `prereg/`: the pre-registration documents, written before the analysis.
- `data/`: the curated reference set with quote anchors, the per-row results,
  the metric summaries, the curation log, and the screen-probe summaries.
- `db/`: `qme.db`, the verified-ledger database read by the table and
  consistency scripts.
- `scripts/`: the analysis, figure, and table code, plus `requirements.txt`.
- `figures/`, `tables/`: output folders the scripts write into; the committed
  copies live under `paper/`.

## Reproducing the numbers

Tested on Python 3.13.

```
git clone https://github.com/Krishnatejavepa/qme-paper-validation.git
cd qme-paper-validation
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt

QME_ROOT="$PWD" python scripts/make_tables.py
QME_ROOT="$PWD" python scripts/fig1_parity.py
QME_ROOT="$PWD" python scripts/fig2_residuals.py
QME_ROOT="$PWD" python scripts/fig3_decomposition.py
QME_ROOT="$PWD" python scripts/step2_bias_corrected.py
QME_ROOT="$PWD" python scripts/d1_offset_verdict_70_560.py
QME_ROOT="$PWD" python scripts/consistency_check.py
```

What to expect:

- `consistency_check.py` prints `69/69 PASS` and exits 0 (58 Na-screen checks plus
  11 D1 calibration-audit checks, each tied to a number in the paper).
- Figure 2 returns the residual correlation r = -0.939.
- Table II reports the pre-registered primary metric of 1.09 V (raw held-out
  MAE 0.668 V, corrected 0.802 V).
- Table VI lists the seven verified-ledger voltages, LiCoO2 4.120 V through
  Na3Fe2(PO4)3 3.5976 V.
- `d1_offset_verdict_70_560.py` regenerates `data/d1_corrected_offsets.json`
  byte-for-byte: offset sd = 0.31 V over four couples, verdict FAIL.
- The regenerated tables and the step-2 outputs match the committed copies. The
  figure PDFs match in content; exact bytes depend on the matplotlib build.

Two scripts are kept for provenance and do not run from a clean checkout:
`s3b_litexp.py` needs a Materials Project API key and the trained model weights,
and `bib_verify.py` needs network access. (`d1_offset_analysis.py` is a retired
pointer to `d1_offset_verdict_70_560.py`.) The numbers in the paper come from the
committed outputs above, so none of these is needed to reproduce them.

## Calibration audit (Section VI)

The paper also runs a pre-registered offset audit of our own PBE+U bench against
four benchmark Li couples, with the gate fixed before any run: an offset standard
deviation below 0.15 V is calibratable, at or above 0.30 V retires
absolute-voltage claims. The audit fails. The four offsets are +0.31, +0.48,
+0.43, and -0.20 V, with a standard deviation of 0.31 V, above the 0.30 V bar, so
absolute-voltage language is retired from our own ledger in favor of ranking-only
claims. The failure is not numerical noise: the layered-Co and Fe-phosphate
couples share a +0.41 V offset to within 0.09 V while the Mn spinel sits apart,
which points to a per-chemistry offset rather than a single global one. The
verdict is also cutoff-invariant: at the pre-registered charge-density cutoff the
evaluable couples already disperse with a standard deviation of about 0.68 V, more
than twice the bar.

The gate and the converged-cutoff deviation are documented in
`prereg/D1_PREREGISTRATION_2026-06-10.md`. The verdict is regenerated from the
committed energies by `scripts/d1_offset_verdict_70_560.py` into
`data/d1_corrected_offsets.json`, and `consistency_check.py` ties each of those
numbers to the paper text.

## License

Code in `scripts/` is under the MIT license (`LICENSE`). The data, database,
figures, and paper (`data/`, `db/`, `figures/`, `tables/`, `paper/`) are under
CC-BY-4.0 (`LICENSE-CC-BY-4.0`).

## Citation

```
@misc{vepa2026,
  author = {Vepa, Krishna Teja},
  title  = {Computational references are not experiments: pre-registered
            validation of machine-learned sodium-cathode voltages},
  year   = {2026},
  eprint = {ARXIV_ID_PENDING},
  archivePrefix = {arXiv},
  primaryClass  = {cond-mat.mtrl-sci}
}
```
