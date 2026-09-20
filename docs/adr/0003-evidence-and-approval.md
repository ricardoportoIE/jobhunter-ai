# ADR-003 — Evidence, scoring and approval

Status: adopted for phase 1 implementation; refined through confirmed preferences. Date: 2026-09-19.

## Proposed decision

Versioned facts and approved evidence are the factual source. An LLM may extract or explain, but cannot create facts or alter the score. Package approval and submission authorisation are separate objects tied to versions.

## Scoring v0.2

Brief weights: skills 30, experience 20, portfolio 15, education 10, location/working arrangement 10, salary 5, authorisation/hours 5 and strategy 5; total 100.

Each category contains explicitly structured and reviewed criteria. Per criterion: `met=1`, `partial=0.5`, `unmet=0`; `unknown` is excluded from the average. Required criteria have an internal weight of 2 and desirable criteria 1. Text similarity does not prove fulfilment. Strategy uses the user's explicit assessment, never an invented preference.

For category c: `attainment_c = sum(weight_i × attainment_i) / sum(known weight_i)`; null if nothing is known. `coverage_c = sum(known weight_i) / sum(applicable weight_i)`. In this first version, a category without criteria receives coverage 0 and attainment null; the reviewer must fill in relevant requirements before relying on the result.

`effective_weight_c = category_weight_c × coverage_c`.

`score = 100 × sum(effective_weight_c × attainment_c) / sum(effective_weight_c)`; null if the denominator is zero. `coverage = sum(effective_weight_c) / 100`. Use decimal half-up rounding to 2 decimal places, only for the final result. Display score and coverage side by side so that partial analysis is not presented as complete.

Example: skills with attainment 0.8 and coverage 1, experience with attainment 0.5 and coverage 1, all other categories unknown → score 68, coverage 0.5 → `REVIEW`, without an automatic positive recommendation.

An explicitly unmet disqualifying requirement → `BLOCKED`, regardless of score. An unknown disqualifying requirement (except future authorisation/sponsorship possibilities) or coverage < 0.70 → `REVIEW`. Otherwise: 85–100 `PRIORITISE`; 70–84 `APPLY_AFTER_REVIEW`; 55–69 `REVIEW`; below 55 `TRACK_OR_ARCHIVE`. The blockers list preserves the reason and evidence. Missing information is not a confirmed blocker.

Authorisation to start work and a recommendation to pursue an offer are separate dimensions. Unknown sponsorship, the need for new permission or the current hours limit do not by themselves block a full-time search. Record `employment_gate=REVIEW_BEFORE_START` and flags; only a confirmed explicit incompatibility constitutes a blocker. Apply the [matching policy v0.2](../phase-0/matching-policy.md). Do not treat this unknown as fulfilment; coverage for the authorisation category remains unknown.

These are product decisions to calibrate. Job/profile snapshots, evidence, weights, the algorithm and criterion assessments must suffice to reproduce the result; the algorithm version also identifies skill aliases and rounding rules.

## Approval

Future `Approval` object: ID, authenticated actor, scope (`package` or `submission`), application ID, profile/job versions, package hash, recipient/channel for submissions, timestamp, expiry and decision. Package rejection does not become employer rejection.

The transition and audit event are atomic. Repeated approval is idempotent; a payload change invalidates the decision. Sensitive fields require explicit review for each field. An LLM cannot create or expand any approval.

## Alternatives and consequences

Delegating scoring entirely to an LLM was rejected because it hinders reproducibility. Storing only the CV was rejected because it does not provide provenance for each claim. Requiring evidence and snapshots adds initial review work, but makes packages explainable and allows them to be invalidated correctly.
