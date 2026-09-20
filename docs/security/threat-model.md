# Initial threat model

Status: local controls, AI validation, document rendering and P4 connectors are implemented and tested. Cloud and submission controls remain scheduled for later phases. See [runtime security and data](../phase-1/security-and-data.md) and [P4 validation](../phase-4/validation.md). Initial validation owner: project maintainer. Real data remains separate in `.private/`; only synthetic examples and derived data without contact details may be versioned. See [trust boundaries](../architecture/overview.md).

Assets: factual profile, personal data, documents, source/provider credentials, approvals, history and budget. Potential attackers: a malicious source, submitted file, unauthorised session or compromised dependency.

| ID / priority | Threat and impact | Planned control | Verification and phase |
|---|---|---|---|
| T01 / P0 | A job advert injects instructions to steal the profile or invoke tools | Delimit content as data; minimal tools; authorisation policy outside the LLM; strict schema | A malicious fixture must not execute a tool; phase 2 |
| T02 / P0 | A URL/redirect accesses metadata, localhost or a private network | Allowlist, HTTPS, validated DNS resolution pinned to the connection, block non-public IPv4/IPv6 addresses, revalidate redirects, byte/time limits | Test metadata, IPv6, DNS rebinding and redirects; before fetching |
| T03 / P0 | An unauthorised user reads a CV or approves an application | Authenticated session, ownership checks on every resource, CSRF for cookies, expiry and invalidation | API without the correct session/actor returns 401/403; phase 1 |
| T04 / P0 | An LLM invents experience or uses an expired fact | Facts verified for use/validity; validator outside the generator; mandatory evidence coverage | An unsupported or revoked skill blocks the package; phase 3 |
| T05 / P0 | Replay or an old approval submits the wrong version | Hash, versions, scope, expiry, lock and idempotency; reconcile ambiguous outcomes | Repeat the decision and simulate a timeout after submission; phases 3/6 |
| T06 / P0 | A malicious CV/attachment compromises the renderer | Check extension and signature, expansion/size limits, no macros, isolated renderer without networking and with a temporary filesystem | ZIP bomb, macro, path traversal and CPU limit tests; before upload |
| T07 / P0 | PII/secrets leak through Git, logs or prompts | Separate private data, redaction, secret scanning, minimal context, provider review | Capture failure logs and fixture diffs; phases 1/2 |
| T08 / P1 | Workers and the browser have excessive permissions | IAM per task, tool/destination allowlist, isolated network, short-lived tokens | An attempt to access an out-of-scope resource must fail; phases 5/6 |
| T09 / P1 | History is altered and loses its audit value | Application role cannot update/delete events; event written in the transaction; integrity export | Test rollback and SQL permissions; phases 1/5 |
| T10 / P0 | An agent loop or polling generates unexpected costs | Call/token/time limits, ledger with atomic budget reservation, bounded retries | Two concurrent tasks cannot exceed the reserved balance; phase 2 |
| T11 / P1 | A compromised or vulnerable dependency | Lockfiles, dependency/secret analysis, least-privilege CI, reviewed updates | PR checks; before using each dependency |
| T12 / P1 | Loss or improper restoration of personal data | Private backup, rehearsed recovery, reapply deletions, lifecycle policy | Restore in an isolated environment with test data; phase 5 |
| T13 / P0 | External text becomes HTML/script in the browser | Escape by default, no raw HTML; sanitise if necessary; CSP on deployment | XSS in titles/descriptions/evidence does not execute; phase 1 |

## Retention, logging and approval

P4 connectors use fixed provider hosts, pinned public DNS, rejected redirects, byte/time
limits and serialised reads. Sources require a current access review. OAuth state is
single-use, session-bound and expires after ten minutes; PKCE and same-origin CSRF
protection cover code exchange. Tokens use context-bound Fernet encryption outside
exported records. Gmail reads only the chosen label, rechecks message labels and does
not follow email links or request attachment downloads. Pending advert changes block
new matching/strategy use and invalidate dependent packages. Tests cover these controls
with synthetic provider data; Google's production verification remains an external requirement.

Logs contain correlation IDs, duration, counts, error codes and costs, without full profile, prompt or CV bodies. Record decision summaries and evidence, without the model's internal reasoning. Append-only auditing is a control against the application role; do not promise absolute immutability against administrators.

The proposed retention policy is in the [Candidate Knowledge Base](../phase-0/candidate-knowledge-base.md). Encrypt data in transit and at rest on deployment. Review data submission and retention for each model/provider, including regional routing, before using personal data.

## Residual risks and response

Automatic fact-checking can fail and approved evidence can be wrong; retain human review. An external provider receives authorised context: minimise data and allow access to be revoked. A source may change its terms: suspend the connector until a new review. AWS is ephemeral and canonical state remains local; export and recovery precede teardown. RPO 24h/RTO 8h are initial local targets to demonstrate, not a guaranteed SLA. When the budget is reached, prevent new spending and allow actions that end existing costs; alarms alone do not guarantee the ceiling.

If an incident is suspected: stop workers/submissions, revoke affected credentials, preserve only necessary evidence with restricted access, assess the impact, fix the issue and record resumption. Specific legal obligations need their own assessment before public launch; this document describes technical project controls.
