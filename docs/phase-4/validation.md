# P4 validation

## Live connection follow-up — 22 September 2026

The operator reported a failure after Google consent. A diagnostic inside the running
API container reproduced an unreachable IPv6 route while IPv4 connected. The transport
previously selected only the first validated DNS address. It now tries alternatives
within the overall deadline, before sending any HTTP request. TLS verification and
public-address checks remain in place; OAuth POSTs are never automatically replayed.
Temporary network/provider failures now have distinct, translated feedback.

The operator confirmed a successful live Gmail connection after the rebuilt service
was installed. A read-only status check confirmed the source was connected and still
paused. No mailbox content was read for this diagnosis; label selection and alert import
remain separate user actions. The original delivery's validation record below is
preserved as historical evidence.

Regression checks passed: 152 API tests without skips and 31 frontend tests. Ruff and
format checks passed; mypy passed in an isolated Linux container because Windows
Application Control blocked a local mypy DLL. Tests explicitly clear real Gmail
credentials from the shared test settings and use synthetic provider responses.
The rebuilt application's smoke check passed. Network regression tests cover fallback
in both address-family orders, all-address failure, the overall deadline and actionable
OAuth errors without credential exposure.

The Gmail browser journey passed on desktop and mobile with synthetic Google
responses. Initial frontend/browser runs hit time limits while other local checks
were running; the frontend passed with one worker and the browser rerun passed after
the API suite finished. No assertions or timeout thresholds were relaxed.

## Original delivery — 20 September 2026

Local review date: **20 September 2026**. P4 extends the existing application without
changing AI models, prompts or deterministic scoring weights. All automated provider
responses are synthetic; paid AI calls are not part of this regression suite.

## Automated coverage

| Layer | Result | Main checks |
|---|---|---|
| API and database | 145 tests passed; none skipped | Ownership, source reviews, atomic batches, deduplication, changed adverts, stale approvals, OAuth, encrypted secrets and recovery |
| Frontend components | 31 tests passed | Explicit consent, source controls, preserved input on failure, comparison before replacement and OAuth return handling |
| Browser | 16 tests passed on desktop and mobile | Existing application journeys plus discovery, Gmail connection, custom label selection, link hand-off and disconnect |

The Python suite reports two existing upstream deprecation warnings. Ruff, mypy,
ESLint, TypeScript, Prettier and production package/frontend builds passed. npm audit
reported no known vulnerabilities. The recorded P1, P2, P3 and model-comparison
contracts are checked offline, preserving their original results and limitations.

Discovery tests exercise incomplete boards, missing posts, conditional responses,
throttling, rejected redirects, response limits, bounded transient retries, revoked
tokens, replayed/expired OAuth state, session binding, label boundaries, ignored
attachments, expired pagination cursors, interrupted leases and configuration races.
Source changes cannot silently replace a saved review. New matching and package work
is blocked until a pending content change is reviewed; a missing listing alone is
not treated as confirmed closure.

Browser tests use Microsoft Edge locally and Chromium in CI. They include axe checks,
Portuguese feedback, keyboard-accessible controls and a 320-pixel viewport. Discovery
and Gmail screenshots were visually reviewed. OAuth tests simulate Google's redirect
and token services while exercising the application's actual consent, state, PKCE,
callback and encrypted-storage paths, including React StrictMode's effect lifecycle.

## Reproduce

Follow the complete commands in [local development](../local-development.md). Use a
separate database whose name starts with `jobhunter_test`; skipped database tests do
not count as full validation. The five CI jobs run API, frontend, browser, Docker
Compose and design/documentation checks. The new Gmail configuration helper is also
included in CI formatting and lint checks.

```powershell
python scripts/smoke_local.py --exercise-db-recovery
python scripts/check_documentation.py
```

The recovery check temporarily stops only the project's database and restarts it
without deleting data. The API must remain live, report not-ready during the outage
and become ready after recovery. The discovery worker has its own heartbeat check.
Account erasure and interrupted-worker recovery are also covered with disposable
database records in the API tests.

The rebuilt API, database, frontend and discovery worker were healthy. The local
database outage/recovery smoke check passed without restarting the API or frontend.
The configuration helper passed an isolated temporary-file check for importing a
client, preserving an existing encryption key and rejecting an unregistered redirect
without changing the destination. Secret/publication scans and the documentation
check passed, including private authored documentation and frozen evidence checks.

## Live evidence and remaining configuration

A single live Greenhouse read on the review date returned 12 vacancies and cache
validators from `fosphamarketing`. No recurring source was enabled automatically.
This validates the public connector request, not every employer's board or terms.
See [progress](progress.md) for the source-access review boundary.

**Live Gmail validation remains pending:** the operator has no Google OAuth client
yet and requested preparation of the integration and configuration. Follow
[Gmail setup](gmail-setup.md) to register a web client, connect an account, select a
custom alerts label and review access before enabling checks. Synthetic tests do
not establish Google application verification or successful access to that account.

No application submission, email sending, attachment fetching or unrestricted
website crawler is introduced. Retention, limits and recovery procedures are in
[operations](operations.md). Private source documents, actual credentials, mailbox
content and local exports remain outside version control.
