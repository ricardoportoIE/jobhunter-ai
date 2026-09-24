# ADR-006 — Controlled local submission rehearsal

Status: adopted for P6. Date: 24 September 2026.

## Decision

Implement one local sandbox channel. It accepts a reviewed application payload and
returns a durable simulated receipt. It makes no network request, sends no email and
does not mark an application as submitted to an employer. Existing manual submission
records retain their meaning. AWS remains off; no paid inference is required.

Use the existing PostgreSQL records, transactions and owner locks for checkpoints.
No orchestration framework is needed for this bounded workflow. A future external
adapter requires its own channel permission, credentials, outcome reconciliation and
tests; the sandbox is not evidence that an employer accepts automated applications.

## Authorisation and state

Preparation requires a current approved package and a current reviewed analysis with
no application blocker or unresolved clarification. Starting work remains a separate
gate: a condition to resolve before employment does not automatically block applying.
Authorisation binds the actor, application, package revision, exact payload digest,
fixed sandbox recipient, channel and a 15-minute expiry. Package approval alone is
insufficient. Changes to source evidence, profile, vacancy, analysis or package require
fresh preparation and authorisation. Cancellation revokes an unused authorisation.

The persisted states are `NEEDS_REVIEW`, `APPROVED`, `DISPATCHING`, `UNKNOWN`,
`FAILED`, `CANCELLED` and `SIMULATED`. Checkpoint `DISPATCHING` before calling the
channel. A second transaction writes the receiver's receipt; a third records completion.
The receiver is idempotent per application and verifies the payload digest. Repeated
clicks cannot create another receipt. Every state change is audited atomically.

An interrupted or ambiguous attempt must be reconciled against the receiver, without
resending. A definitive absence permits a fresh review; an unavailable receiver leaves
the outcome unknown. The sandbox serialises receiver acceptance and reconciliation
with the same owner lock, preventing a late acceptance after a definitive absence.
Completion records a sandbox event in the tracker without changing its real status.

## Acceptance

Test authorisation, ownership, CSRF, expiry, revoked sources, stale revisions,
application blockers, cancellations, duplicate/concurrent requests, interruption
before and after receiver acceptance, unavailable reconciliation and recovery across
application restart. Exercise review and resumption in desktop and mobile browsers.
Report measured outcomes separately from proposed performance targets. No real
application submission is authorised by implementing or testing P6.
