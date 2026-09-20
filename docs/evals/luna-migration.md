# Matching with Luna high — implementation and evidence

Local delivery on 20/09/2026. Matching and second assessments use `gpt-5.6-luna` with
`reasoning.effort=high`. Extraction and P3 strategy continue to use GPT-4.1 mini;
Luna was also tested on those tasks. Public research uses Luna high with `web_search`.
The decision combines previous results with the tests below; the new isolated matching
set produced a tie and does not demonstrate general superiority in intelligence.

## Implemented behaviour

- The Responses adapter distinguishes reasoning models from GPT-4.1: Luna receives `reasoning`
  without `temperature`; mini receives temperature zero. No automatic retries or fallback.
- `structured-ids-1.0` contract: fact, evidence and requirement IDs are enumerated from the
  input. Subsequent validation still checks ownership, links, literal citations, permitted uses
  and validity. Groups with more than 250 IDs rely on subsequent validation to limit contract
  size. Valid IDs do not substantiate the response's semantic interpretation.
- The cache distinguishes content, effective schema, contract version, model, effort, prompt,
  output limit and tools. A second assessment uses another operation, preserving both results.
- Reservations include reasoning output and up to three web calls. Unknown usage or usage
  above the reservation blocks new calls until reconciliation. Cached input is conservatively
  accounted for at the standard price; reasoning tokens already form part of output, without double charging.
- Weights and calculations remain in the deterministic engine. Desirable skills do not offset
  an explicit blocker. Pursuing an offer and being able to start work remain separate.
- Unresolved title/body issues, contradictory evidence and unconfirmed disqualifying requirements
  prevent prioritisation. A note does not turn an unknown requirement into a met one.
  Clarifications record the conclusion, source, responsible person and versions. Confirmed blockers remain.
- Different assessments of the same input appear side by side. The server checks history even
  when the analysis omits `ai_run_id`. A new disagreement also makes a previous analysis stale.
- Web research is an explicit action: it sends the public question and authorised domains
  without adding the profile, job or documents to the request. It returns clickable citations,
  consultation time and unresolved questions; it changes neither facts nor score. Hour-old history
  is flagged for a fresh query. Consultation time does not prove a page's update date or a correct interpretation.

## Configuration per task

| Task | Prefix after `JOBHUNTER_AI_` | Local model |
|---|---|---|
| Extraction | `PARSING_` | `gpt-4.1-mini-2025-04-14` |
| Matching | `MATCHING_` | `gpt-5.6-luna` high |
| Second assessment | `REVIEW_` | `gpt-5.6-luna` high |
| Strategy | `STRATEGY_` | `gpt-4.1-mini-2025-04-14` |
| Public research | `RESEARCH_` | `gpt-5.6-luna` high |

Each prefix accepts `MODEL`, `EFFORT` and `PROMPT_SUFFIX`. For example,
`JOBHUNTER_AI_REVIEW_MODEL=gpt-4.1-mini-2025-04-14` allows a second assessment with mini.
Effort is sent only to Luna. Prompt suffixes are operator guidance of up to 4,000 characters,
appended to the base instructions; their hash changes the version and cache. Do not put secrets
in them. Source, ownership, budget and calculation rules remain in code.

Base templates: parsing `job-parser-1.3`, matching `evidence-matching-1.2`, strategy
`application-strategy-1.1`, research `public-research-1.0`. `JOBHUNTER_AI_MODEL` remains the
legacy fallback. New models require price/capability registration, contract tests and evaluation;
the application neither accepts arbitrary identifiers nor promotes models automatically.

Luna uses up to 8,000 output tokens by default, including reasoning; configurable limit from
1,000 to 16,000. Mini remains at 5,000. API timeout: 180s; Nginx: 240s. These limits affect caching.

## New evaluation and live results

[Holdout frozen](../../data/evals/migration-holdout.json) in commit `5ced489`, before calls:
eight new synthetic cases, two models, two runs per case. Includes a long advert, combined and
alternative requirements, a numeric minimum, diploma versus MSc, conflicting evidence,
contradictory title/body and malicious commands in the advert. Labels are assistant-authored.

| Final matching, 16 responses per model | GPT-4.1 mini | Luna high |
|---|---:|---:|
| Valid responses | 16 | 16 |
| Statuses matching the original label | 14 | 14 |
| Unsupported positives on labelled criteria, before filters | 0 | 0 |
| Statuses changed by filters | 0 | 0 |
| Cases with different statuses between repetitions | 0 | 0 |
| Additional clarification flags where the label did not require them | 0 | 3 |

**H05 label defect:** the text states that there has never been a production deployment, but
the label was frozen as `unknown`. Both answered `unmet` in both repetitions, consistently with
the explicit negative. We preserved the dataset and 14/16 count; we did not correct the answer
key afterwards to increase the score. Luna's three additional flags are review costs to examine,
not a presumed advantage. Stability here measures status across only two repetitions, not all
wording or every warning.

The HTTP workflow uses the `jobhunter_test_migration` database and a synthetic candidate,
passing through real routes: extract → populate draft → simulated review → matching → calculate →
P3 fact selection → approve strategy → generate documents → approve → download ZIP/DOCX/PDF →
invalidate source. All paid calls also reserve cost in the main ledger; the disposable database
does not bypass the monthly limit. The personal profile is unchanged. Approvals are explicit
test steps, not the user's approval of a real application.

| Final HTTP workflow | GPT-4.1 mini | Luna high |
|---|---|---|
| Long advert, no conflict | Complete | Complete |
| Contradictory title/body | Matching rejected by the validator | Complete, `REVIEW` recommendation |

In the rejected case, mini classified an advert disagreement as conflicting evidence and
supplied only one fact, violating the semantic contract. No score or document was produced
for that workflow. The failure remains in the report; we did not repeat until a favourable response appeared.

Before enum constraints, one Luna call changed a character in a fact's UUID. The validator
blocked the non-existent reference. That failure prompted the new contract and a complete
rerun with both models, retaining the [baseline](../../data/evals/migration-live-baseline.json).
The baseline also preserves four interruptions caused by the test runner omitting fields
in review, and one Luna extraction that left the role null when faced with a conflict.
Subsequent simulated review records manual entries separately; they do not count as model successes.

The live web test made one Responses call with three searches, restricted to official Irish
sources. It returned the Critical Skills Employment Permit page and explicitly stated that
it had not confirmed the editorial date, without deciding individual eligibility. The server
validated domains, citation ranges, usage and cost. The result remains subject to human checking.

Artefacts: [final results and raw responses](../../data/evals/migration-live.json),
[runner](../../scripts/evaluate_migration.py). Total for this delivery: **93 Responses calls**
(49 baseline + 44 final), including three internal web search calls.
Accounted cost: **€0.17025100** (€0.06787750 + €0.10237350), with a 1.25 EUR/USD allowance;
this is a conservative project estimate, not an invoice or exchange-rate quote.

## Real user decisions

[Three explicit labels](../../data/evals/user-decisions.json), separate from the synthetic answer key:

- REAL-01: discard. The stated reason, studying in Dublin, is not confirmed in the snapshot;
  it is stored as a user rationale to verify, without becoming a factual job requirement.
- REAL-10: prioritise; a project objective.
- REAL-12: retain in scope, with role clarification because the title and body conflict.

These decisions concern historical snapshots. They neither prove the offers remain open nor
form a complete eligibility gold set. They were not sent to the model as expected answers.

## Verification and reassessment

Local checks: 89 API tests, 13 React tests and six desktop/mobile Playwright workflows with
Edge; type checking, lint, Docker build and local smoke test. Playwright includes cited research
and a second assessment with disagreement. DOCX/PDF preserved the approved fact literally;
downloads for changed sources were blocked. P3 document layout remains as verified in the previous phase.

```powershell
uv run --project apps/api python scripts/evaluate_migration.py --check
uv run --project apps/api python scripts/compare_reasoning_models.py --check
uv run --project apps/api python scripts/compare_reasoning_models.py --check --protocol refined
```

`evaluate_migration.py --live` is explicit, limits the additional reservation to €1 per run,
retains existing successes and preserves failures. Use `--retry-pipeline` only after diagnosing
the cause; it archives previous attempts in the report. For another round, preserve the previous
report and freeze new inputs/labels before querying models. Do not reuse this holdout as
independent evidence after adjusting prompts based on it.

Promotion criteria: critical errors, unsupported claims, consistency and review effort first;
then suitability for each task. Price and latency are operational metrics. No small sample
guarantees the absence of reasoning limitations or future errors. The Luna alias may change:
record models, effort, prompt, contract, raw responses and new human decisions in each round.

Prices checked on 20/09/2026: [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
US$0.20/M input and US$1.20/M output; [web search](https://developers.openai.com/api/docs/pricing)
US$10/1,000 calls, plus content tokens. Usage follows the
[web search API](https://developers.openai.com/api/docs/guides/tools-web-search).
