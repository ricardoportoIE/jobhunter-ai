# P4 — Discovery and alerts

The delivery adds opt-in sources to the local application. It does not send email,
submit applications or silently replace reviewed evidence. Each stage receives a
local commit after its checks; the complete phase is pushed only after final review.

| Stage | Scope | Status |
|---|---|---|
| P4-01 | Owned source registry, access reviews and persistence contracts | Implemented |
| P4-02 | Greenhouse reader, synchronisation, revisions and deduplication | Pending |
| P4-03 | Gmail OAuth, dedicated-label reader and configuration guide | Pending |
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
