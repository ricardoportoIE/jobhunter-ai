# P4 — Discovery and alerts

The delivery adds opt-in sources to the local application. It does not send email,
submit applications or silently replace reviewed evidence. Each stage receives a
local commit after its checks; the complete phase is pushed only after final review.

| Stage | Scope | Status |
|---|---|---|
| P4-01 | Owned source registry, access reviews and persistence contracts | Implemented |
| P4-02 | Greenhouse reader, synchronisation, revisions and deduplication | Implemented |
| P4-03 | Gmail OAuth, dedicated-label reader and configuration guide | Implemented; live connection awaits credentials |
| P4-04 | Discovery interface, preference hints and company research hand-off | Pending |
| P4-05 | End-to-end validation, security review and operational documentation | Pending |

## Source controls

Sources start disabled. Activation requires a recorded purpose/permission reference,
explicit confirmation and a review expiry within 90 days. The initial frequency is
daily. Expired reviews prevent execution even if the saved toggle remains enabled.
Only board tokens are accepted for Greenhouse; arbitrary connector endpoints are not
configurable. Gmail requires a connected account and a custom alerts label.

The source, run and opportunity records use existing ownership and version checks.
OAuth secrets use a separate table excluded from ordinary exports and snapshots;
account erasure removes them. Migration 007 is additive and leaves existing data intact.

## External dependencies

The user has no Google OAuth client yet. Implement and test the complete integration
with synthetic responses, document setup and report live Gmail validation separately.
No mailbox connection or live Gmail test is claimed without that configuration.

## P4-02 checks

Sixteen focused API tests passed, covering source reviews, synchronisation, conditional
reads, throttling, pause races, access denial, isolated ownership, incomplete results,
promotion and existing manual deduplication. Ruff and mypy passed.

On 20 September 2026 a single public Greenhouse read of `fosphamarketing` returned
12 vacancies, a complete response and cache validators. No scheduled source was
enabled and no original advert content was added to the repository. The public API
contract was checked against the [official reference](https://docs.greenhouse.io/job-board.html).
The generic platform terms page did not load during review; it is not treated as
permission for recurring collection. Activation still requires the operator's
applicable employer/platform permission reference and expiry.

The worker checks one due source each minute. Successful reads are cached for a day;
failed reads wait at least 15 minutes and honour longer Retry-After values. Access
denial disables the source. A database lock serialises provider reads, and a five-minute
lease records interrupted work. Each complete response is saved atomically. Partial
responses and failures never imply that a vacancy has closed. Missing posts are labelled
**not listed**, while reviewed jobs remain untouched. New and changed versions retain
provenance; older changed versions are retained in the private export.

## P4-03 checks

Nineteen focused tests passed across Gmail, discovery and privacy. They cover OAuth
configuration, PKCE, consent, state replay/expiry, rejected scopes, encrypted storage,
export exclusions, disconnect, token refresh, label boundaries, malicious HTML and
attachment/body limits. Ruff and mypy passed. See [Gmail setup](gmail-setup.md) for the
operator steps and the explicit distinction between synthetic and live validation.
