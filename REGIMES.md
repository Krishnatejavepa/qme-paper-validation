# Two regimes of DFT-referenced machine learning

One page on where foundation-model materials work ends and where QME begins.
The claim is complementarity, not competition.

## Regime 1: reference errors cancel

Universal machine-learned interatomic potentials and materials foundation
models (MACE-MP-class potentials, GNoME-class discovery pipelines, and their
successors) are trained on large DFT corpora and evaluated largely against
DFT-level quantities. Inside this regime the systematic error of the DFT
reference mostly cancels, because both sides of every comparison carry it:

- relative energies and rankings within one functional's energy scale,
- structure search, relaxation, and phonons against DFT baselines,
- stability ordering on a hull computed with the same reference,
- interatomic forces for dynamics at DFT fidelity.

This work is real progress and QME does not compete with it. QME itself
borrows a universal potential (MACE-MP-0) for embeddings and screening, on
exactly this internal-consistency logic.

## Regime 2: experiment decides

The regime changes the moment a number leaves the reference's own scale and
meets a decision anchored in the world:

- will this cathode sit inside the electrolyte's voltage window,
- does the predicted plateau clear the threshold that makes a chemistry
  commercially interesting,
- is the synthesized material expected to match the predicted property well
  enough to justify the lab campaign.

Here the reference's systematic error against experiment does not cancel; it
transfers intact into every model trained on it. The numbers in this
repository put magnitudes on that transfer: the Materials Project PBE+U
voltage references sit about 0.54 V below experiment on the compounds where
the comparison is possible, and our own local PBE+U bench failed its
pre-registered single-offset calibration gate (offset sd 0.31 V over four
benchmark couples, against a 0.30 V bar). A model can win every regime-1
benchmark and still carry a half-volt regime-2 offset that no amount of
regime-1 evaluation will ever surface.

## What QME governs

QME is referee infrastructure for regime 2: pre-registered claims, one primary
metric, thresholds fixed before results, exclusions only under pre-committed
rules with sensitivity analyses, negative assertions that survive any outcome,
and verdicts (PASS, FAIL, gray zone) delivered with equal standing. Verdict
artifacts regenerate byte-identically from committed inputs, and validated
claims ship as certificates that state what may and may not be concluded,
always carrying the known reference offsets and ranking-only language for
voltages.

The honest credential is that the first two audits run under this protocol
both FAILED, one of them against our own bench, and both failures are
published with their thresholds, artifacts, and regeneration paths. A referee
that cannot fail its own side is not a referee.

## The complementarity, in one sentence

Foundation models make regime-1 exploration cheap and fast; QME decides,
against experiment-anchored references and under pre-registered rules, which
of the resulting claims are safe to act on in regime 2.
