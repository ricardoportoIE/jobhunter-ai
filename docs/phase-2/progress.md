# P2 — AI job intelligence

Local implementation authorised on 2026-09-20. One commit per stage; no push.

| Stage | Scope | Status |
|---|---|---|
| P2-01 | OpenAI, private secret and contracts | Implemented |
| P2-02 | Atomic reservations, costs, limits and tracing | Implemented |
| P2-03 | Parser with structured output and verified citations | Implemented |
| P2-04 | Normalisation, confidence and interface review | Implemented |
| P2-05 | Embeddings and semantic search | Implemented |
| P2-06 | Potential duplicates identified by similarity | Implemented |
| P2-07 | Evidence-based matching suggestions | Implemented |
| P2-08 | Benchmark, security, E2E and documentation | Completed; live benchmark and acceptance tests run |

Use `git log --oneline --grep=P2-` to find the corresponding commits.

Commits: P2-01 `4b8b424`, P2-02 `5eb0363`, P2-03 `1a177d9`, P2-04 `e403608`,
P2-05 `f2716cc`, P2-06 `831a780`, P2-07 `cb1f95d`. P2-08 is identified by the command above.
See [validation](validation.md) and [operations](operations.md). The real key remains outside Git.

Completion after the US$10 credit: commit `2721c91` fixes parsing/normalisation and matching
based on live tests. The completion commit brings together reports, selection and documentation;
see `git log --oneline --grep=P2`. Total accounted cost €0.13299404 (approximately US$0.1064),
with no pending reservations. 57 API tests, 11 component tests and 4 E2E tests passed.

## Sources verified on 2026-09-20

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): Responses with strict JSON Schema; local validation remains mandatory.
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini): US$0.40 input and US$1.60 output per million tokens.
- [GPT-4.1 nano](https://developers.openai.com/api/docs/models/gpt-4.1-nano): US$0.10 input and US$0.40 output per million.
- [Embeddings](https://developers.openai.com/api/docs/models/text-embedding-3-small): US$0.02 per million tokens.
- [API data](https://developers.openai.com/api/docs/guides/your-data): `store=false` prevents response-state storage; it does not mean Zero Data Retention. Abuse-monitoring logs may retain content for up to 30 days. We do not assume European residency is configured for this account.

One provider explicitly selected by the user. No tools or fallback.
Mini/nano were compared on the 20 cases: mini 20/20 valid, nano 18/20. Mini was selected
for assisted local use; nano also lost a sponsorship condition during documentary review.
Accuracy on the four basic fields does not represent accuracy on all requirements or matching.
Versioned local prices expire after 30 days. Conservative accounting conversion of €1.25/US$,
not an exchange-rate quote. Reservations and totals cover this project, not other applications on the account.
