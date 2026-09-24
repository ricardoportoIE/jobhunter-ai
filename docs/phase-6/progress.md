# P6 — Controlled local submission rehearsal

Every stage receives a local commit after its checks. Push follows final review.
All authored documentation uses British English. AWS resources remain destroyed.

| Stage | Scope | Status |
|---|---|---|
| P6-01 | Channel boundary, authorisation and state contract | Complete |
| P6-02 | Persistent workflow and authorisation guards | Complete; thirteen PostgreSQL acceptance cases and strict types passed |
| P6-03 | Final review, cancellation and resumption interface | Complete; 35 frontend tests, build and both browser sizes passed |
| P6-04 | Idempotent receiver, receipts and reconciliation | Pending |
| P6-05 | Full validation, measured results and final review | Pending |

See [ADR-006](../adr/0006-controlled-submission.md). The implemented channel will
be a local simulation, with no employer delivery or new cloud deployment.
