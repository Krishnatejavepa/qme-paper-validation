# qme-paper-validation

Code, data, and validation protocol for the paper "Computational references are
not experiments: pre-registered validation of machine-learned sodium-cathode
voltages" (Krishna Teja Vepa). arXiv: https://arxiv.org/abs/2606.23725

## The thesis

Machine learning can now generate candidate materials far faster than anyone
can verify them. The binding constraint on ML-driven materials discovery is
therefore not candidate generation; it is trust: deciding which computational
claims deserve belief before money, lab time, or publication space is spent on
them.

The standard practice undermines that trust at the root. ML property screens
are trained and evaluated against computed reference values, for example PBE+U
voltages from public databases, and those references carry their own systematic
error against experiment. A model that reproduces its computed references has
been validated against a ruler, not against the world. On the compounds in this
study where model, database reference, and experiment could all be compared,
the Materials Project PBE+U reference itself sits about 0.54 V below
experiment: the reference, not the model, carries most of the error.

This repository holds the paper's evidence for that claim, the pre-registered
protocol that produced it, and the machinery for anyone to check both.

## The findings, stated plainly

Every verdict below was fixed by thresholds registered before the analysis ran.
Both audits FAILED, and the failures are the results.

**The sodium voltage screen is not screening-grade.** On the audited canonical
set (n=6), raw held-out error 0.67 V, pre-registered conservative metric
1.09 V, and the residual depends strongly on voltage (r = -0.94), so no
additive correction fixes it. The screen was retired on this evidence.

**Our own DFT bench failed its calibration gate.** A pre-registered audit of
the local PBE+U bench against four benchmark Li couples (gate fixed in
advance: offset sd below 0.15 V calibratable, at or above 0.30 V retire
absolute-voltage claims) returned sd = 0.31 V. The verdict is FAIL and is
cutoff-invariant (dispersion roughly 0.68 V at the originally registered
cutoff). Absolute-voltage language is retired from our own ledger in favor of
ranking-only claims. The failure is structured rather than random: the
layered-Co and Fe-phosphate couples share a +0.41 V offset to within 0.09 V
while the Mn spinel sits apart, which points to per-chemistry offsets rather
than one global constant. A pre-registered multi-chemistry survey testing that
per-family hypothesis is in progress.

## The protocol

The durable contribution is the referee procedure, not any single verdict.
QME Validation Protocol v1.0 ([protocol/](protocol/)) fixes, before any result
exists: the claim, one primary metric, complete decision rules including the
gray zone, the exclusion policy (pre-committed rules only, every exclusion
logged, sensitivity analysis mandatory), negative assertions that may never be
made regardless of outcome, per-structure spin states from literature physics,
and operator gates. Verdict artifacts must regenerate from committed inputs.

- Spec: [protocol/QME_VALIDATION_PROTOCOL_v1.0.md](protocol/QME_VALIDATION_PROTOCOL_v1.0.md)
- Machine-readable schema: [protocol/schema/preregistration.schema.json](protocol/schema/preregistration.schema.json)
- This paper's D1 audit as a protocol instance:
  [protocol/instances/prereg_d1_offset_audit_2026-06-10.json](protocol/instances/prereg_d1_offset_audit_2026-06-10.json)

## Layout

- `paper/`: manuscript source (`paper.tex`, `paper.bbl`), the compiled PDF,
  `refs.bib`, and the figures and tables the paper includes.
- `prereg/`: the pre-registration documents, written before the analysis.
- `protocol/`: QME Validation Protocol v1.0 (spec, JSON schema, instances).
- `data/`: the curated reference set with quote anchors, per-row results,
  metric summaries, the curation log, screen-probe summaries, the D1 verdict
  artifact `d1_corrected_offsets.json`, and its provenance manifest.
- `db/`: `qme.db`, the verified-ledger database read by the table and
  consistency scripts.
- `scripts/`: analysis, figure, and table code, plus `requirements.txt`.
- `figures/`, `tables/`: output folders the scripts write into; the committed
  copies live under `paper/`.

## Reproducing the numbers

Tested on Python 3.13.

```
git clone https://github.com/Krishnatejavepa/qme-paper-validation.git
cd qme-paper-validation
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt

bash scripts/verify_reproduction.sh        # one-command D1 reproduction check

QME_ROOT="$PWD" python scripts/make_tables.py
QME_ROOT="$PWD" python scripts/fig1_parity.py
QME_ROOT="$PWD" python scripts/fig2_residuals.py
QME_ROOT="$PWD" python scripts/fig3_decomposition.py
QME_ROOT="$PWD" python scripts/step2_bias_corrected.py
QME_ROOT="$PWD" python scripts/d1_offset_verdict_70_560.py
QME_ROOT="$PWD" python scripts/consistency_check.py
```

What to expect:

- `verify_reproduction.sh` checks the provenance manifest
  (`data/d1_corrected_offsets.json.manifest.json`: sha256 of the artifact, its
  generator, and every committed input), regenerates the D1 verdict artifact in
  a sandbox, and byte-compares it against the committed copy. It prints PASS,
  or a unified diff report if anything differs.
- `consistency_check.py` prints `consistency: 69/69 PASS` and
  `negative guards: 14/14 PASS`, then exits 0. The 69 positive checks tie each
  number in the paper to a committed artifact (58 Na-screen, 11 D1 audit); the
  14 negative guards fail the sweep if any retired claim ("matches experiment",
  "ground truth", novelty language, and so on) regresses into the prose.
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

## Submitting a claim for validation

The same pipeline that audited our own bench can referee an external claim: an
ML-predicted property plus its structure, registered BEFORE the verifying
computation exists.

1. Write a pre-registration JSON conforming to
   [protocol/schema/preregistration.schema.json](protocol/schema/preregistration.schema.json).
   A minimal worked example is
   [protocol/instances/examples/example_external_claim.json](protocol/instances/examples/example_external_claim.json).
   It must fix the claim, one primary metric, PASS and FAIL rules, the
   exclusion policy, negative assertions, and per-structure spin states from
   literature physics.
2. Intake is refused if the claim's datapoints are not all `pending`: a claim
   that arrives with its results already in hand is not a pre-registration,
   and that failure mode is exactly what this protocol referees.
3. What comes back after the operator-gated verification run is a Validation
   Certificate (structured JSON plus a human-readable report): what was
   tested, against which experiment-anchored references, under which
   registered rules, with which verdict, and what may and may not be
   concluded. Every certificate carries the known reference offsets (including
   the MP PBE+U roughly 0.54 V systematic and our own bench's FAILED
   single-offset gate) and certifies voltages in ranking-only language. A FAIL
   is delivered with the same standing as a PASS.

Contact: open a GitHub issue on this repository.

## Where QME sits relative to foundation models

Short version: universal machine-learned potentials and foundation models
mostly operate in a regime where DFT reference errors cancel internally; QME
governs the orthogonal regime where absolute accuracy against experiment
decides real decisions. Complementary, not competitive. The one-page argument
is in [REGIMES.md](REGIMES.md).

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
  eprint = {2606.23725},
  archivePrefix = {arXiv},
  primaryClass  = {cond-mat.mtrl-sci}
}
```
