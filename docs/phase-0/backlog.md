# Actionable phase 1 backlog

Scope: local core without an LLM. IDs are local references, not published issues. Priority P0 = first workflow; P1 = complete the phase. S/M/L sizes are relative, not estimates in days.

**P1-01 to P1-10 implemented locally, with commits at each stage.** [Delivery record](../phase-1/progress.md) and [completed evaluation](../phase-1/evaluation-results.md). Human review of disagreements remains separate from technical validation. The CI workflow is configured; running it on GitHub requires hosting the repository there.

| ID / priority / size | Story and deliverable | Depends on | Acceptance criteria |
|---|---|---|---|
| P1-01 / P0 / M | As a developer, I start the API, web app and PostgreSQL locally | ADR-001 review | Docker Compose with health checks; .env.example without secrets; versions/lockfiles; lint, types, tests and build in CI; local ports |
| P1-02 / P0 / M | As the sole user, I access my data through an authenticated session | P1-01 | Local login, password hash and secret outside Git; session expiry; endpoint ownership; tested 401/403 and cookie CSRF |
| P1-03 / P0 / M | I record facts and evidence and publish a profile version | P1-02 | CRUD, migrations, validity/uses; a verified fact requires review/evidence; review produces a snapshot; synthetic seed example |
| P1-04 / P0 / M | I import job text with provenance and review requirements | P1-02 | Hashed raw content; a URL does not trigger fetching; unknown fields are null; manual confirmation precedes PARSED; size limits and XSS protection |
| P1-05 / P0 / S | I avoid repeating the same job/application | P1-04 | External ID+source, canonical URL and normalised hash; false-merge test; idempotent import and conflict on different payload |
| P1-06 / P0 / L | I see explainable scores, coverage, gaps and blockers | P1-03, P1-04 | ADR-003 v0.2; null without data; a confirmed blocker overrides the score; unknown sponsorship does not block the search; separate employment_gate; persisted snapshots |
| P1-07 / P0 / M | I explore the Inbox and details with evidence | P1-05, P1-06 | Filters, empty/error/loading states, evidence links; score and coverage together; edits invalidate analysis; keyboard navigation |
| P1-08 / P1 / M | I track shortlisted jobs and manual applications | P1-07 | Authorised transitions, timeline; authenticated and confirmed manual record; no submission calls; duplicates prevented |
| P1-09 / P1 / M | I trust the history and protect personal data | P1-03, P1-08 | Atomic event with each change; role cannot update/delete audit records; redacted logs; local export/erasure and rollback tests |
| P1-10 / P1 / M | I demonstrate the complete workflow reproducibly | P1-07, P1-08, P1-09 | Synthetic E2E; local smoke test; run the 20 derived real-world cases; record disagreements and human review; CI checks pass |

## Implementation order

Start with P1-01 and P1-02. Then implement the profile and import, followed by matching, Inbox/details and the tracker. Finish with data protection, the end-to-end workflow and documentation. Each resource's security accompanies its story; P1-09 does not defer authentication or redaction.

## API contracts to implement

| Method / route | Responsibility | Main rule |
|---|---|---|
| POST /api/v1/session | Login | Limit attempts; local secret |
| DELETE /api/v1/session | Logout | Invalidate the session |
| GET, PATCH /api/v1/candidate/profile | Read/edit profile | Optimistic versioning |
| POST /api/v1/candidate/facts | Record a fact | Do not verify automatically |
| POST /api/v1/candidate/evidence | Record a reference | Paths never grant arbitrary filesystem access |
| POST /api/v1/jobs/import | Import text | Idempotency-Key; bounded payload |
| PATCH /api/v1/jobs/{id} | Review fields | Expect the current version; 409 conflict |
| GET /api/v1/jobs and /jobs/{id} | List/details | Pagination, filters and ownership |
| POST /api/v1/jobs/{id}/analyse | Deterministic matching | Versioned profile/job |
| GET /api/v1/matches/{id} | Result and evidence | Reproducible snapshot |
| POST /api/v1/applications | Create a shortlist entry | Candidate/job uniqueness |
| GET /api/v1/applications | Tracker | Filters and pagination |
| POST /api/v1/applications/{id}/events | Transition/manual record | Validate state, actor and confirmation |

Use a consistent error format with a code, message and correlation ID, without sensitive content. No functional submission endpoint in phase 1. The future implementation generates the OpenAPI contract; it is not written as a promise that an endpoint already exists.

## Tests completing the first slice

Migrations against a test PostgreSQL database; domain/scoring and validity unit tests; authenticated API; idempotency and concurrency; XSS protection; audit integration; E2E import → review → analyse → open evidence. Include missing salary, unknown/unmet disqualifying requirements, revoked facts and changed profiles. Do not make paid calls in CI.

## Later backlog

Phase 2: inference adapter, parsing, dataset benchmark and cost ledger with reservations/limits of €10 for AI and €25 combined. Phase 3: CV/letter and package approval. Phase 4: read-only Greenhouse pilot and Gmail with a dedicated label, without sending. Phase 5: temporary Terraform infrastructure with a €15 AWS preflight, TTL, export and verified teardown. Phase 6: controlled submission through a permitted channel. These items are outside phase 1 implementation.
