# QME Validation Protocol v1.0

**Status:** v1.0.0 (operator-approved at Gate 1, 2026-07-01).
**Schema:** [`schema/preregistration.schema.json`](schema/preregistration.schema.json)
**Instances:** [`instances/`](instances/)
**Date:** 2026-07-01

---

## 1. Purpose

QME is the trust layer for ML-driven materials claims: the referee infrastructure that
decides which computational claims deserve belief. This protocol is the referee's rulebook.
It is the contribution that survives any single study; the D1 offset audit and the
multi-chemistry offset survey are its first two instances, not its definition.

The protocol exists because the field's failure mode is structural, not accidental:
ML materials screens are trained and judged against computed references (typically
PBE+U database voltages) that carry their own systematic error against experiment.
On the compounds where model, database reference, and experiment could all be compared,
the Materials Project PBE+U reference sat about 0.54 V below experiment. A claim
validated only against computed references has not been validated. This protocol fixes
what a real validation must contain, before any result exists, so that the verdict
cannot be reverse-engineered from the outcome.

## 2. Definitions

- **Claim.** A single falsifiable statement about a computational method or model,
  stated so that FAIL is a publishable outcome.
- **Anchor.** An experiment-anchored literature value with recorded conditions
  (couple, polymorph, temperature, source). Computed values are never anchors.
- **Datapoint.** One unit of evidence the verdict statistic is computed over
  (for voltage audits: one couple's offset δ = V_computed − V_experiment).
- **Verdict.** The outcome of applying the pre-committed decision rules to the
  primary metric. One of: `PASS`, `FAIL`, `GRAY_ZONE`,
  `excluded_reproduction_inconclusive`.
- **Exclusion.** Removal of a datapoint from the verdict statistic. Legitimate only
  under a rule written before results existed.

## 3. Requirements

A study conforms to this protocol if and only if all of the following hold.

**R1. Registration precedes results.** The claim, primary metric, decision rules,
anchor set, method parameters, and exclusion rules are committed to version control
before any result they govern exists. The commit is the evidence.

**R2. One primary metric.** Exactly one pre-named statistic decides the verdict.
Secondary analyses may be reported but cannot change the verdict.

**R3. Complete decision rules.** The mapping from metric values to verdicts covers
the whole range, including an explicit gray zone with pre-registered handling
(operator decision, documented at decision time, never retro-fitted). A FAIL is
reported with the same prominence as a PASS.

**R4. Exclusions are pre-committed, logged, and stress-tested.** No datapoint is
dropped except under a rule in the registered exclusion policy. Every exclusion is
logged (no silent dropping) and triggers a sensitivity analysis reporting the verdict
with and without the excluded point. When reproduction of an underlying result is
inconclusive, the honest state is `excluded_reproduction_inconclusive`, not a quiet
re-run until agreement.

**R5. Negative assertions are registered and mechanically guarded.** Every study
enumerates the claims that must NOT be made regardless of outcome (for QME voltage
work: no absolute-voltage claims after the D1 FAIL, ranking-only language, computed
values never called ground truth, corpus-absence never called novelty). Where a
mechanical guard exists (`consistency_check.py`), the assertion names it.

**R6. Deviations are disclosed, justified, and invariance-checked.** Any departure
from registered parameters is recorded as a post-registration addendum with its
justification and, where demonstrable, evidence that the verdict does not depend on
the deviation. Precedent: the D1 cutoff correction (50/200 Ry registered, 70/560 Ry
final) is disclosed in the verdict artifact together with the FAIL-at-both-cutoffs
invariance check.

**R7. The reference-error caveat travels with every number.** Any reported voltage
carries the applicable reference caveats: the local bench's own calibration status
(D1: single additive offset FAILED, sd 0.31 V over n=4; per-chemistry offset
admissible on the n=3 core) and the database-reference systematic (MP PBE+U about
0.54 V below experiment on the audited compounds). Ranking-only language unless a
pre-registered calibration gate has PASSED for the relevant chemistry family.

**R8. Spin states from literature physics only, documented per structure.** Every
registered structure records its spin manifold, the expected converged total
magnetization, and the literature basis (established oxidation states, spin states,
and the FM computational convention). Manifolds are never tuned to improve agreement.
A pair half that converges outside its registered manifold excludes that datapoint
under R4.

**R9. Operator gates.** At minimum: no compute before the operator approves the
registered slate, and no ledger write before the operator reviews the verdict.
Autonomous stages stop at gates; ambiguity means stop and ask.

**R10. Verdict artifacts are regenerable.** The verdict is a structured JSON artifact
plus the script that regenerates it from committed inputs, byte-identically where the
toolchain permits, with an explicit diff report where it does not. Provenance
manifests (file hashes, environment, prereg reference) are the Phase 2 extension of
this requirement.

## 4. Lifecycle

```
 1. REGISTER   claim, metric, thresholds, anchors, method, exclusion rules,
               negative assertions -> committed (R1)
 2. GATE       operator approves the slate (R9); no compute before this
 3. EXECUTE    staged runs; spin manifolds checked against registration (R8)
 4. BANK       results recorded as-is; failed or off-manifold runs disclosed
 5. VERDICT    generator script applies the registered decision rules (R2, R3);
               exclusions logged with sensitivity analysis (R4)
 6. GATE       operator reviews verdict before any ledger write or publication (R9)
 7. PUBLISH    verdict artifact + regeneration path + caveats (R7, R10);
               FAIL stated as plainly as PASS
```

## 5. Machine-readable pre-registration

The schema at [`schema/preregistration.schema.json`](schema/preregistration.schema.json)
(JSON Schema draft 2020-12) encodes the requirements above as a document format.
The human-readable registered markdown remains the document of record; the JSON
instance is its machine-readable form and says so in `registration_evidence`
(with a `retrofit_note` when transcribed after registration, as for the two
founding instances).

Required blocks: `claim`, `primary_metric`, `decision_rules`, `exclusion_policy`
(with `sensitivity_analysis_required` and `silent_exclusion_forbidden` locked to
true), `negative_assertions`, `method` (including per-structure spin states under
`literature_physics_only`), `datapoints`, `artifacts`, `operator_gates`.

Verdict states: `PASS`, `FAIL`, `GRAY_ZONE`, `excluded_reproduction_inconclusive`.
Datapoint states: `pending`, `banked`, `included`, and the `excluded_*` family.

## 6. Instances registry

| Instance | Registered | Canonical document | Status |
|---|---|---|---|
| [`d1_offset_audit_2026-06-10`](instances/prereg_d1_offset_audit_2026-06-10.json) | 2026-06-10 | [`prereg/D1_PREREGISTRATION_2026-06-10.md`](../prereg/D1_PREREGISTRATION_2026-06-10.md) | Verdict LOCKED 2026-06-28: **FAIL** (sd 0.31 V, n=4) |
| `offset_survey_2026-06-29` | 2026-06-29 | private working repo | Multi-chemistry survey, Phase C executing; the instance ships with the survey publication |

A worked external-claim example lives at
[`instances/examples/example_external_claim.json`](instances/examples/example_external_claim.json).

## 7. Versioning

The protocol is semantically versioned. Patch: wording that changes no requirement.
Minor: new optional schema fields or new requirements that do not invalidate existing
instances. Major: anything that would make an existing conforming instance
non-conforming. Instances pin the protocol version they conform to
(`protocol_version`); a verdict is always read against the protocol version it was
registered under.
