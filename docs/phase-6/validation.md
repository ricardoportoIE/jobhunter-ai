# P6 validation record

Date: 24 September 2026. Scope: local sandbox orchestration, synthetic records and
the existing application regression suite. No real application was submitted and
no AWS resource was created. This validates controlled simulation, not employer
integration or recruitment outcomes.

## Measured results

| Check | Result |
|---|---|
| API and database suite | 192 passed; zero failures, errors or skips |
| P6 API coverage within that suite | 27 cases: 13 authorisation/acceptance cases and 14 recovery/source-boundary cases |
| Frontend suite | 36 passed, including five P6 component cases |
| Browser suite | 16 passed across desktop and mobile |
| P6 browser journeys within that suite | 2 passed; both extend strategy, sensitive-answer review, document approval and download through sandbox recovery |
| Infrastructure controller, host and Terraform | 18 + 7 + 3 passed; no AWS deployment |
| Total automated cases and Terraform runs | 272 |
| Python types | 79 source files passed strict mypy checks |
| API suite elapsed time | 49.814 seconds, from the JUnit report |
| P6 browser journey elapsed times | 7.7 seconds desktop; 7.0 seconds mobile in the recorded full browser run |
| Duplicate receipts or unauthorised acceptances | Zero in the tested scenarios |
| Paid inference calls and AWS deployments | Zero |

The counts include different test types, not 272 distinct user journeys. Browser
times include test interactions and assertions; they are not request latency, a
recovery objective or a production performance benchmark. The
[metrics snapshot](metrics.json) records these values without personal identifiers.

## Acceptance and recovery coverage

- Package approval alone cannot execute a rehearsal. Missing confirmation, a different
  payload digest, outdated package versions, invalid ownership and CSRF tokens fail.
- Authorisation expires after 15 minutes. Cancellation revokes it, and a fresh preparation
  returns to review. Exact prior approval/payload revisions remain in private snapshots.
- Profile, job, package, evidence, analysis and application changes invalidate delivery.
  Expired facts and changed or missing discovery sources are checked again. Application
  blockers and unresolved clarifications remain gates; future employment review retains
  its separate meaning.
- A lost acknowledgement before or after receiver acceptance enters `UNKNOWN`, without
  automatically resending. A new application instance recovers both cases from PostgreSQL.
- A failure after acceptance but before completion leaves `DISPATCHING`; reconciliation
  finds the receipt and completes the tracker event exactly once.
- Concurrent execution and reconciliation produce at most one receipt. Definitive absence
  closes the old attempt before a delayed receiver can accept it. An unavailable lookup
  remains unresolved; a mismatched receipt cannot become a success.
- The payload excludes source evidence and internal reasoning. The caller cannot choose
  Gmail, an external recipient or another channel. Receipts are explicitly simulated,
  and the real application status remains unchanged.
- Desktop/mobile journeys cover cancellation, reauthorisation, page reload, an aborted
  response after server acceptance, receipt recovery and persistence after another reload.
  axe reported no violations on the receipt screen; no horizontal overflow was found.
  The mobile receipt screenshot was also inspected visually. A component regression
  keeps reconciliation available when the real application has been withdrawn.
  After that final interface adjustment, all 36 component tests and four affected
  desktop/mobile package and manual-tracker journeys passed again (28.0 seconds for
  the focused browser run).

## Regression checks and environment

Ruff, formatting, mypy, ESLint, TypeScript, Prettier, wheel/source packaging and the web
build passed. Frozen P1/P2/P3 evaluation contracts and both reasoning-comparison
protocols passed offline. Phase-0 schemas, rejection cases, dataset split isolation and
budget contracts passed. Authored documentation was reviewed and checked separately.

The disposable Compose workflow passed twice with synthetic data. Backup digest and
restored record verification passed; its containers, network and volume were removed.
The everyday local stack was rebuilt without deleting its data. Smoke checks verified
frontend assets, API, PostgreSQL, proxy and OpenAPI, followed by a database outage:
readiness returned 503, liveness remained 200 and service recovered without restarting
the API or frontend.

API and browser tests ran in Linux containers because Windows application controls
block the managed local Python interpreter. Frontend checks ran locally. Isolated
test databases and synthetic credentials kept personal data outside the tests.
Two existing upstream Python deprecation warnings remain; there were no skipped API
tests. Initial environment setup failures were resolved before the recorded successful
runs and are not counted as passes.

Raw logs, JUnit output, browser evidence and synthetic recovery artefacts remain under
ignored `.private/` paths. CI repeats the full checks without AWS or model credentials;
results are available in [GitHub Actions](https://github.com/ricardoportoIE/jobhunter-ai/actions/workflows/ci.yml).

## Limits

The sandbox accepts one successful rehearsal per application and uses the same local
database for its independent receipt transaction. A real provider's asynchronous
behaviour, permission terms, availability, acknowledgement formats and retention have
not been validated. P6 introduces no external sender, cloud worker, production SLA or
new claim about matching accuracy. A real channel needs a separate, explicitly scoped
pilot. The P5 infrastructure remains destroyed; historical billing may still arrive.
