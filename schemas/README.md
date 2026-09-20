# Data contracts v0.2.0

[domain.schema.json](domain.schema.json) uses JSON Schema Draft 2020-12 and contains six main entities in `$defs`. It is a design contract, not a database migration or Pydantic implementation.

| Entity | Responsibility | Main invariants |
|---|---|---|
| Job | Job snapshot, provenance and requirements | Unknown fields are null; a URL does not authorise fetching; programmatic sources require a review reference |
| CandidateFact | Versioned atomic claim | verified requires evidence, a reviewer, a date and permitted uses |
| Evidence | Source reference and location | Private content by reference; review records actor and date |
| MatchResult | Reproducible score and coverage | Eight categories; references to profile/job versions and algorithm |
| Application | Application lifecycle | Approved package identified by hash; manual submission separate from the adapter |
| CandidateProfile | Snapshot and preferences | Facts referenced by revision ID; constraints and master CV remain private |

All listed properties are required; use null for unknown values where permitted. Empty arrays represent the absence of records. UUIDs are identifiers, timestamps use UTC with `Z`, scores range from 0 to 100 and coverage/confidence from 0 to 1. `additionalProperties: false` prevents unexpected fields from being silently accepted.

In v0.2.0, MatchResult requires `employment_gate` and `review_flags`. The recommendation to pursue an offer is separate from the conditions for starting work. `REVIEW_BEFORE_START` requires at least one flag. Unknown sponsorship does not by itself prevent a positive recommendation. Local data was migrated from v0.1.0 to v0.2.0; see the [policy](../docs/phase-0/matching-policy.md).

Extraction `confidence` may be null and is not evidence or approval. `coverage` measures assessed data and is not a statistical probability. The example's `fixture://` references and repeated hashes are declared placeholders; for real data, calculate SHA-256 over the specified canonical bytes and store a resolvable reference in authorised storage.

## Rules still requiring domain validation

JSON Schema validates structure, types and some local conditions. It does not itself validate:

- Existence, ownership and review of referenced evidence; temporal validity and permitted uses at the time of the operation.
- `valid_until >= valid_from`, minimum salary <= maximum salary and expiry after the decision.
- Eight distinct categories and weights totalling 100; correspondence between assessments and requirements; score/coverage and blocker calculations under [ADR-003](../docs/adr/0003-evidence-and-approval.md).
- A reviewed profile with valid facts/evidence and sufficient constraints for the intended use.
- Permitted transitions, event consistency, idempotency and concurrency.
- Approval by an authorised actor, current hash and versions, scope, recipient, validity and reviewed sensitive fields.
- Package invalidation after revocation; reconciliation of a submission attempt with an unknown outcome.
- URL, path and file-byte security.

These rules belong to phase 1 stories or the phase introducing the operation. The example also undergoes reference and basic consistency checks, without claiming that a domain engine is already implemented.

## Versioning

An incompatible change requires a new `schema_version` and explicit data migration. Fact revision IDs remain immutable. The API may expose smaller views and exclude sensitive content; these schemas do not authorise publishing the entire object in the frontend.

## Validation

Run `python scripts/validate_phase0.py` in an environment with [requirements-phase0.txt](../requirements-phase0.txt). The script checks the metaschema, examples, fixture references, rejection cases and local documentation links. It uses neither network access nor credentials. The `jsonschema` dependency is used only to validate contracts in this phase.
