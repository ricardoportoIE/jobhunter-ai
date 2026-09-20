# P3 — Delivery validation

Local execution on 2026-09-20. Synthetic test data, separate from the personal profile.

## Automated tests

- API: 69 tests, including permissions per use, consent, invalid selection, versioning,
  separate approval of sensitive answers, idempotency and diffs.
- Security: user isolation, authentication, CSRF, rejection of unknown IDs,
  AI payload minimisation and export/erasure of packages and snapshots.
- Documents: downloads blocked before approval, file hashes in the ZIP, identical facts
  in DOCX/PDF, empty author metadata and changed sources blocked.
- Frontend: 11 React tests; TypeScript, ESLint, Prettier and production build.
- Browser: 6 Playwright workflows covering P1, P2 and P3 on desktop/mobile. P3 covers
  strategy → approval → generation → sensitive answer → new version → diff →
  approval → PDF download. No horizontal overflow in either viewport.
- Ruff, mypy, evaluation contracts and local Docker stack smoke checks.

HTTP/browser tests use a deterministic provider and `jobhunter_test*` databases.
The live tests below exercise the strategy and budget service with OpenAI;
they are not a complete browser run against the external API. The CI workflow includes
new tests and the offline report check; it has not run remotely.
The two Starlette/httpx and AnyIO deprecation warnings already recorded in P2 remain.

## Live OpenAI calls

Six live calls were made: three cases with the initial prompt and three with the final
`application-strategy-1.1` prompt, using the configured GPT-4.1 mini.
Cases: normal selection, malicious instructions within the advert and commercial
experience/MSc gaps. Each call was repeated through the cache without a new charge.

The first result confused a diploma's relevance with fulfilment of an MSc requirement
in its explanation. The final prompt makes the qualification distinction explicit and
states that a personal project cannot replace commercial years. The final case identifies
both gaps. Document claims always came from canonical facts.

The three final cases passed: valid IDs, claims copied from facts, no invented experience
in documents, salary/visa questions without automatic answers, approval blocked while
answers are missing, DOCX/PDF rendering and valid caching.

| Run | Estimated ledger cost |
|---|---:|
| Baseline, prompt 1.0 | €0.00382700 |
| Final, prompt 1.1 | €0.00418800 |
| Total P3 | €0.00801500 |

Equivalent to approximately US$0.006412 at recorded rates, before the 1.25 accounting
allowance used in the ledger. This is neither an exchange-rate conversion nor a wallet
balance query. Public reports contain only synthetic data:
[baseline](../../data/evals/phase3-live-baseline.json) and
[final](../../data/evals/phase3-live.json). They are not a human gold-set benchmark and
do not establish general strategy accuracy or qualification equivalence.

Reproduce without external calls, from the root:

```powershell
uv run --project apps/api python scripts/evaluate_phase3.py --check
```

Explicit external test, subject to monthly limits and a maximum additional reservation
of €0.25; existing results may be served from the cache:

```powershell
uv run --project apps/api --env-file .env python scripts/evaluate_phase3.py --live
```

## Visual verification

Synthetic CV and letter samples were generated in both formats. ReportLab PDFs were
rendered to PNG and inspected. DOCX files were converted with the documents skill's
`render_docx.py` helper in an isolated QA container with LibreOffice and Poppler,
without networking during conversion. This container is not part of the application runtime.

All four samples have one page each, with a black title, consistent margins, legible text
and no clipping/overlap. The coloured border inherited from the Word template was removed
from the styles used. Screenshots of the approved package on desktop and mobile were also
inspected. QA artefacts are in `.private/p3-qa/` and `apps/web/test-results/`, ignored by Git.

DOCX and PDF share structured content; fonts and pagination may vary between renderers.
The HTML preview supports content review without promising identical pagination to the
final file. Sample inspection does not replace review of each personal document before submission.
