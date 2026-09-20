# Runtime contracts — phase 1

OpenAPI at `/api/openapi.json` is the executable reference. Phase 0 v0.2 schemas remain design contracts and historical fixtures; they are not identical runtime serialisers. The implementation uses `version` for concurrency on all records, server-generated UUIDs and ownership derived exclusively from the session.

## Implemented decisions

- Storage: JSONB records typed/validated by Pydantic, relational owner/kind/version metadata, identity and uniqueness indexes, separate snapshots and append-only auditing. No microservices were adopted and no empty packages created.
- Profile: any fact/evidence change increments the version and returns the profile to draft. Publication creates an immutable snapshot. Facts retain evidence versions; changing evidence requires fact review before it can support a positive assessment again.
- Evidence: `content_sha256` hashes the excerpt/declaration supplied by the user; it does not prove that a remote file was downloaded or validated. References do not open arbitrary files.
- Job: import preserves the full text and its hash; editing replaces structured fields and requires `expected_version`. `review_confirmed` permits PARSED. SCORED is derived metadata and does not alter the version of reviewed fields. A new edit invalidates analysis through version comparison.
- Matching: the user assesses criteria and links facts. Text similarity is not proof of fulfilment. Positive assessments without a valid fact become unknown. Career strategy uses explicit assessment. Advanced seniority confirmed in a structured field creates a blocker; incidental mentions and mixed levels do not.
- Authorisation: the unknown disqualifying requirement exception applies only when the category is authorisation/hours and `future_authorisation=true`. It is not legal confirmation or permission to start work.
- Idempotency: the `Idempotency-Key` header is bound to the actor/operation/hash. Without a header, an exact repeated payload has a derived key. A different payload with the same key returns 409. Reimporting an existing identity does not overwrite reviewed content.
- Deduplication: ID+source, URL preserving identity parameters and normalised hash+location. No semantic/fuzzy merge. The same reference with conflicting locations requires review; identical content in different cities remains separate.
- Tracker: only implemented states are accepted; package generation/approval stages are deferred to phase 3. SHORTLISTED/RESEARCHED can record SUBMITTED only with confirmation, date, channel and evidence of manual submission. This does not invoke email or a portal.
- Ownership failures return 404 to avoid confirming another owner's record exists. Missing sessions return 401; invalid origin/CSRF returns 403. Errors contain a code, safe message and correlation ID.

## Routes additional to the backlog

`GET /api/v1/session`, `POST /api/v1/candidate/profile/review`, fact/evidence `GET/PATCH/DELETE`, `GET /api/v1/jobs/{id}/matches`, `GET /api/v1/applications/{id}` and `GET /api/v1/candidate/export` complete the interface workflow. Login and health checks are the only data endpoints without a session; Swagger/OpenAPI are also available only in the local environment.

Real phase 0 data was not imported automatically. The synthetic seed is optional and refuses a profile that already has facts. Test data uses databases whose names begin with `jobhunter_test`.
