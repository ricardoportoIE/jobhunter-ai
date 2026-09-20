# Selected sources and access rules

Research date: 2026-09-19. Initial channel: user-supplied text, with URLs used only as provenance. First future automatic pilot: Greenhouse Job Board API, starting with a small, relevant board (`fosphamarketing`). Gmail is the first email provider; OAuth and dedicated-label reading enter only in phase 4. No mailbox was accessed in this phase.

## Source register

| Source | Current scope | Decision |
|---|---|---|
| Manual text | Local import authorised by the user | Selected for phase 1 |
| Public Greenhouse | GET selected adverts for research and evaluation | One-off research completed; scheduler/connector still disabled |
| Greenhouse Fospha pilot | One board, reading and deduplication | Selected; fresh purpose-specific terms review before enabling polling |
| Gmail | Dedicated alerts label; no sending or modification | Selected for phase 4, not connected |
| Lever | Later alternative | Not implemented |
| Automated LinkedIn | Login, scraping and applications | Blocked |

The official documentation states that GET is public without authentication and separates authenticated submission. The one-off query used only documented endpoints. Public technical access is not a broad licence to redistribute content. Use only derived/paraphrased facts in the repository and preserve private originals. [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html).

Detailed references and decisions for each snapshot are in the private register. The generic terms URL consulted did not respond; this was recorded and was not treated as permission for continuous polling. Before phase 4, confirm applicable platform/employer terms, purpose, retention and frequency. Without a sufficient basis, retain manual import and do not enable the board.

## Future connector contract

ID, domain/board, endpoints, purpose, terms URLs, review date/owner, decision, limits and next review. Only `ENABLED` permits scheduled execution. GET with concurrency 1, caching, initial daily polling, a 15s timeout, up to 2 transient retries and respect for Retry-After. Stop on 401/403 and never bypass CAPTCHA. Revalidate DNS/IP and redirects against SSRF. Email does not authorise automatically following embedded links.

## Delivered dataset

Twenty real adverts selected from official endpoints, with 12 records for development and 8 for evaluation. [Derived data](../../data/evals/real-cases.json) and [report](evaluation-report.md). Originals, hashes, timestamps and URLs are in `.private/evaluation/`. The analysis includes one case outside the target market, one confirmed duplicate and one real title/description conflict.

Assistant-written labels are design expectations, not human gold-standard labels. Human agreement, accuracy and calibration evaluation will be recorded when the matching workflow is implemented. The synthetic dataset remains separate and was not counted as real vacancies.
