# P3 — Application Package Generator

Implementation authorised on 2026-09-20, with local commits per stage.

| Stage | Scope | Status |
|---|---|---|
| P3-01 | Contracts, usage permissions and snapshots | Implemented: `12c9e19` |
| P3-02 | Strategy, review and versioned generation | Implemented: `7a8e16b` |
| P3-03 | CV, cover letter, answers and DOCX/PDF/JSON downloads | Implemented: `b52dde7` |
| P3-04 | Approval screen, differences and evidence | Implemented: `3f61251` |
| P3-05 | Live tests, security, rendering and documentation | Completed; `test(P3-05)` commit in local history |

Principle: AI selects facts and explains the strategy. Document claims are extracted
literally from the approved base, preserving dates, employers and roles. Factual corrections
are made in the canonical base and require regeneration. Templates use British English.
Contact details and manual answers are explicit user declarations, stored locally.
Strategy and package require separate reviews. Approval does not submit an application.

See [usage](operations.md) and [validation and limitations](validation.md).
