# Completed evaluation — phase 1

The 20 public cases derived from real adverts were run using the `deterministic-manual-0.2.0` engine and conservative job identity rules. [Reproducible result](../../data/evals/phase1-results.json). Command: `uv run --project apps/api python scripts/evaluate_phase1.py --check`.

## Scope and results

This is a conservative public-data baseline, **without the private profile or invented positive assessments**. The adapter uses already structured fields (title, level and mentioned skills); it neither extracts free-text semantics nor turns expected labels into inputs. Phase 1 relies on manual review to structure requirements and assess fulfilment. The test does not measure suitability against the real CV, AI parsing accuracy or employability.

| Check | Result |
|---|---|
| Cases run | 20: 12 development and 8 evaluation |
| Expected blockers, unknown score and review before starting | 20/20 |
| Recommendation agreement after mapping taxonomies | 12/20 |
| Cases with any difference in recommendation, flags or duplication | 18/20 |
| Human gold standard | Unavailable; human review pending |

The original set uses `DEPRIORITISE`, `SECONDARY` and `PURSUE_WITH_REVIEW`, which are not score v0.2 enums. The report declares the mapping used for comparison. The 12/20 figure is not a measure of product accuracy.

## Recorded disagreements

- REAL-05/06/07/18: labels suggest deprioritising based on experience or education. Without reviewed facts and explicit assessment, the engine retains REVIEW, null score and zero coverage. No portfolio is automatically converted into employment years or a diploma.
- REAL-10: the label permits pursuing the junior vacancy. The engine retains REVIEW without an assessed profile; absent sponsorship information creates no blocker.
- REAL-11/13/16: secondary career priority needs explicit assessment. The engine does not invent preferences.
- REAL-11/13: public paraphrases have different text and exclude source IDs/URLs. Conservative identity rules do not confirm the documentarily annotated duplicate. Merging across boards with different boilerplate requires manual review or a later duplicate-candidate detection stage.
- Flags such as title/body conflict, enrolment, B2B, graduation window, clearance and missing MSc require reviewed requirements/assessments. The baseline does not implement free-text parsing outside phase 1 scope.
- Explicitly senior/staff levels are blocked; mixed-level roles remain for review. Incidental text such as ‘collaborate with senior engineers’ does not trigger blocking.

## Human review

Each case has `human_review.status=pending` in the report. No human decision was assumed. The reviewer must confirm the differences above, correct requirements/assessments where needed and record agreement or disagreement with a reason. Original labels remain preserved; they were not adjusted to improve results.

The complete functional workflow with a synthetic profile and explicit assessments is verified separately by integration and E2E tests. That workflow proves execution and traceability; it does not replace a human pilot with real data.
