# P2 validation — 2026-09-20

**P2-01 to P2-08 completed for local use with human review.** After the user added
US$10 and authorised testing, we ran real parsing, matching and embedding calls.
GPT-4.1 mini remains the default, now with a recorded comparison. No real candidate CV
or facts were sent in these tests. The key remains exclusively in the backend.

## Live benchmark

20 derived public cases, two models, prompt/normaliser `job-parser-1.3`.
[Full results and review](../../data/evals/phase2-benchmark.json).

| Model | Valid outputs | Correct basic fields in valid outputs | p50 / p95 | Accounted cost |
|---|---|---|---|---|
| GPT-4.1 mini | 20/20 (100%) | 79/80 (98.75%) | 2.559 / 3.351 s | €0.02443300 |
| GPT-4.1 nano | 18/20 (90%) | 71/72 (98.61%) | 2.276 / 2.823 s | €0.00610580 |

The fields are title, company, location and country; nano's denominator excludes two rejected
responses. Counting failures as incorrect fields, nano scores 71/80 (88.75%). No refusals.
All accepted citations were verified through substrings and offsets. Gates: ≥95% valid
outputs and ≥95% basic fields. Mini passes both; nano fails the first.

Documentary review by the assistant, **not a human gold standard**:

- REAL-12: mini shortened the annotated title; it remains counted as an error. It flagged
  the title/body contradiction. We did not alter the label to improve the metric.
- REAL-17: nano declared sponsorship available, losing the restriction to certain roles.
  Mini retained unknown and presented the conditional excerpt for review.
- REAL-11: salary without a numeric value remains unknown. A literal explanation of its
  absence becomes a review note, without creating an amount or confidence in a non-existent value.
- Importance, category, requirement completeness and interpretation of contextual text
  still require human correction, including for mini. Examples: REAL-03/07/08/14/18.

Previous runs were preserved: [1.0](../../data/evals/phase2-benchmark-baseline.json),
[1.1](../../data/evals/phase2-benchmark-1.1.json) and [1.2](../../data/evals/phase2-benchmark-1.2.json).
They revealed empty salary objects, reconstructed citations and confusion between an absent
value and evidence of absence. Normalisation accepts only literal excerpts and retains nulls;
invented citations and unsupported values remain rejected.

The same 12 development and 8 evaluation cases were repeated during adjustments;
**the evaluation set is no longer an untouched holdout**. Personal matching accuracy,
confidence calibration and human agreement require new reviewed cases in the pilot.
This limits general quality conclusions without preventing assisted, reviewed P2 use.

## Functional acceptance

| Check | Result |
|---|---|
| Python/API/PostgreSQL | 57 tests passed |
| React components | 11 tests passed |
| Playwright desktop/mobile | 4 complete workflows passed, isolated synthetic provider |
| Ruff, formatting and strict mypy | Passed |
| ESLint, Prettier, TypeScript, Vite and wheel | Passed during implementation; no frontend change in this completion |
| Compose, migrations, restricted runtime, proxy and smoke | Passed; services healthy |
| Live adversarial parsing | Salary extracted; malicious instruction flagged; sponsorship not invented |
| Live matching with synthetic evidence | Python supported; commercial employment, authorisation and career unknown |
| Real embeddings | 256 dimensions; Python result ranked above cooking; cache without a new charge |
| Real HTTP through Docker/Nginx | Login/CSRF → extraction → cache → draft → review → index → search → duplicate → archive |
| User data | Profile unchanged; synthetic jobs archived; test session ended |
| Secret in versionable files, Git history and web assets | Not found by exact-match verification |

Artefacts: [AI evidence](../../data/evals/phase2-live-acceptance.json) and
[HTTP workflow](../../data/evals/phase2-http-acceptance.json). Matching was exercised through the
real service with the same validation/ledger; HTTP integration and the reviewed score are covered
by synthetic E2E. Simulated transport is not treated as evidence of real inference quality.

Additional coverage: authentication, CSRF, ownership, invented citations, invalid schemas,
refusals, incomplete outputs, injection as data, concurrent reservations, retries/cache, combined
limit, expired prices, timeout, month rollover, reconciliation, erasure during inference,
embedding versions, conflicts between cities and consent for each evidence record.
The manual P1 workflow remains covered.

## Usage and completion

Project ledger after all tests: **€0.13299404**, approximately **US$0.1064** at recorded
prices. Includes four comparisons of 40 calls, diagnostics and live tests, including 38 rejected
responses. There are 138 successes, 38 invalid responses and the two initial HTTP 429 responses
without tokens. Pending reservations: €0; unknown costs: none. The local €1.25/US$ conversion
is an accounting allowance; these figures are not a bill or wallet balance query.

The €10/month AI and €25 combined ceilings were preserved. The €15 accounting reservation
for AWS is not AWS consumption. No publication, application submission or external message.
Local commits are recorded in [progress](progress.md); no push. CI is configured but has not
run on GitHub. Known test warnings: Starlette/httpx and AnyIO deprecations, not suppressed.
