# Local P2 operations

## Status and configuration

The user selected OpenAI. The supplied key was imported into `.env`, which is ignored
by Git, without displaying it. Only the API receives the key; it is absent from the frontend and images.
The first two checks received HTTP 429. After the user added US$10 and authorised tests,
parsing, matching, embeddings and the real HTTP workflow were validated. See the
[evaluation results, usage and limitations](validation.md).

To configure/replace the key, run from the root:

```powershell
python scripts/configure_openai.py C:\private\path\openai-key.txt
docker compose up --detach --wait api
```

The importer accepts exactly one key, does not print its value and preserves other options.
Use `docker compose config --quiet` to validate configuration without printing secrets.
The original file in Downloads was preserved.

| Setting in `.env` | Default / limit |
|---|---|
| `JOBHUNTER_OPENAI_API_KEY` | Backend-only secret |
| `JOBHUNTER_AI_MODEL` | `gpt-4.1-mini-2025-04-14`, selected in the benchmark for reviewed use |
| Additional permitted models | `gpt-4.1-nano-2025-04-14`, `gpt-5.6-luna` |
| Matching / second assessment | `JOBHUNTER_AI_MATCHING_MODEL` / `JOBHUNTER_AI_REVIEW_MODEL`: Luna high |
| Extraction / strategy | `JOBHUNTER_AI_PARSING_MODEL` / `JOBHUNTER_AI_STRATEGY_MODEL`: mini |
| Public research | `JOBHUNTER_AI_RESEARCH_MODEL`: Luna high, up to 3 searches per call |
| Embeddings | `text-embedding-3-small`, 256 dimensions |
| `JOBHUNTER_AI_MONTHLY_EUR` | €10; may be reduced |
| `JOBHUNTER_COMBINED_MONTHLY_EUR` | €25; full €15 reservation for AWS |
| `JOBHUNTER_AI_EUR_PER_USD` | 1.25: accounting allowance, not an exchange-rate quote |
| `JOBHUNTER_AI_PRICES_REVIEWED` | 2026-09-19 UTC / 2026-09-20 in London; expires after 30 days |

Before updating the review date, check the official sources in the [phase record](progress.md)
and adjust `PRICES` if needed. Each run preserves the prices and allowance used.

## Interface workflow

1. **Import job → Extract with AI:** sends only the advert and displays fields/requirements
   with literal citations and declared confidence, which is not yet calibrated.
2. **Populate draft for review:** transfers fields without publishing. Correct them and confirm
   review. A citation confirms the text's origin, not the correctness of its interpretation.
3. **Assess requirements:** select up to 20 facts to send with their evidence excerpts.
   Sensitive, revoked, expired or unreviewed facts and those without valid evidence are excluded.
   With no selected facts, the result is unknown without calling the API.
4. Check suggestions, fill in assessments and confirm them to calculate. AI does not produce
   the score; P1's deterministic engine preserves snapshots and the link to the suggestion.
5. **Semantic search:** index one record at a time, then search. Sends a fact's claim or the
   job text; the query also generates a vector. Vectors and search remain local.
6. **Potential duplicates:** uses text and existing vectors without an external call. Confirmation
   archives the current job and preserves the primary job and histories. Conflicting location/company
   details need correction first. Similarity never triggers an automatic merge.
7. **AI activity:** shows status, tokens, duration, costs, reservations and usage alerts.

There are no background AI calls. Advert URLs are references without automatic fetching.
**Consult current public information** allows explicit searches within selected domains,
with citations and human checking. **Request a second assessment** preserves disagreements.
Task configuration, prompts and evidence are in the [Luna migration](../evals/luna-migration.md).
No application or message is sent. The action names above are English descriptions of the interface.

## Costs, repetition and recovery

Reservations are confirmed in PostgreSQL before the external call. Content/model/prompt/schema
identify the operation. Repeating a success reuses its result; concurrent requests with the same
input are blocked. The SDK does not retry automatically. After correcting a failure's cause,
use the retry-after-correction action. The limit is two attempts per content item in 24h.

A timeout, transport failure, HTTP 408/5xx or unknown usage retains the reservation. A `running`
execution older than five minutes also blocks new allocations. After checking provider usage,
reconcile administratively without assuming zero cost:

```powershell
uv run --project apps/api --env-file .env python -m jobhunter_api.ai_admin RUN_ID --confirmed-eur CONFIRMED_AMOUNT --billing-checked
```

Invalid responses/refusals with tokens are accounted for. Reservations carry across month boundaries.
The limits protect this application, not other uses of the key/account, taxes or unreviewed price
changes. The €15 reservation neither creates AWS resources nor queries AWS billing. Local totals
are not an invoice. Data erasure does not reset the budget.

## Benchmark and optional live tests

From the root, to run the 20 public cases with both candidates:

```powershell
uv run --project apps/api --env-file .env python scripts/evaluate_phase2.py --live --max-additional-eur 1
uv run --project apps/api --env-file .env python scripts/validate_phase2_live.py --live
```

Without `--live`, there are no calls. Additional limit: €1, always within the monthly ceiling. Report:
`data/evals/phase2-benchmark.json`. Saves each result, reuses successes, stops at blocks and does
not promote a model automatically. For an already corrected failure, `--attempt 2` permits a
second attempt within the daily limit. No private document is part of this dataset.

The second command runs synthetic checks of adversarial parsing, salary, matching, embeddings
and caching, with up to €0.25 additional spending within the monthly ceiling. It does not change
the candidate profile. Result: `data/evals/phase2-live-acceptance.json`. Completed calls are reused.
A new benchmark run replaces the report at that path with unreviewed results;
use `--output ANOTHER_PATH.json` to preserve the selected final report.

Technical gates: ≥95% valid outputs and ≥95% correct basic fields; non-existent citations
are rejected. Human review must assess requirement interpretation, unknowns, refusals,
false duplicates and matching. Paraphrased/pseudonymised data is not a human gold standard.
This parsing benchmark does not measure the candidate's matching accuracy.
In the final run, mini passed the gates; nano failed validity and lost a sponsorship restriction.
The original split was reused during adjustments and is not an untouched holdout.
The assistant's documentary review is recorded; human review remains mandatory for each job
before scoring. These results do not imply human approval of a gold set.

## Privacy and limitations

- Responses uses `store=false`, without fallback. Tools are exclusive to explicit public
  research; extraction, matching and strategy do not browse. This does not mean Zero Data
  Retention. The [official controls](https://developers.openai.com/api/docs/guides/your-data)
  describe possible retention in abuse logs for up to 30 days. We do not assume European residency.
- Matching sends the job title/text/requirements, selected facts and excerpts, without a display
  name or document references/paths. PDFs/DOCX files are not sent automatically. Suggestions and snapshots remain local.
- Export includes runs and the index. Administrative erasure removes text, results, vectors and
  personal links, retaining costs without an owner. An in-flight response cannot restore its
  result after erasure. Files and provider retention are separate.
- Structured input is conservatively bounded by bytes to 200,000 tokens. Mini: up to 5,000
  output tokens; Luna: 8,000 by default, configurable up to 16,000, including reasoning.
  Network timeout is 180s and Nginx timeout 240s. Research reserves 200,000 input tokens and up
  to three searches; usage above the limit requires reconciliation. No automatic agent loop.
- Embeddings use 1,000-character chunks. Search supports 5,000 current chunks and up to 10
  results, excluding edited, archived, revoked records and those without valid evidence.
- Duplicate detection compares up to 500 active jobs and displays 20 candidates. Jaccard ≥0.65
  or cosine ≥0.90 are heuristic thresholds without real-world calibration yet.
- Projects/courses do not automatically substantiate professional experience. Career strategy
  remains unknown in automatic suggestions.

## Tests without charges

In `apps/api`:

```powershell
$env:JOBHUNTER_TEST_DB_NAME = 'jobhunter_test'
uv run --locked --env-file ../../.env pytest
uv run --locked mypy
uv run --locked ruff check . ../../scripts/evaluate_phase2.py ../../scripts/configure_openai.py
uv run --locked ruff check ../../scripts/validate_phase2_live.py
uv run --locked python ../../scripts/evaluate_phase2.py --check
```

In `apps/web`: `npm run lint`, `npm test`, `npm run build`, `npm run test:e2e`.
On the validated Windows environment, set `$env:PLAYWRIGHT_CHANNEL='msedge'` for E2E. Fixtures
are only in `apps/api/tests`, outside the production image, without a real key or paid calls.
