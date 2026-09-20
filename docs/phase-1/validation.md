# Final phase 1 technical validation

Run locally on 2026-09-20. Implemented in ten stages with local commits; no remote publication.

| Check | Result |
|---|---|
| API: Ruff + formatting + strict mypy | Passed |
| API: unit/PostgreSQL integration tests | 36 passed; none skipped in the complete run |
| Web: ESLint + Prettier + strict TypeScript | Passed |
| Web: Vitest/jsdom | 9 passed |
| Browser E2E: 1440px desktop + emulated mobile | 2 passed in headless Edge 153 |
| Builds | Python wheel/sdist, Vite bundle and Docker images passed |
| Compose with an empty database | Migrations, restricted role, three healthy services and smoke test passed |
| HTTP smoke | Assets, direct/proxied API, OpenAPI and PostgreSQL readiness passed |
| Database recovery | Liveness 200 during the outage; readiness 503 and return to 200 without restarting API/web |
| Design contracts | Public phase 0 validator passed |
| Derived real-world dataset | 20 cases run; results and disagreements versioned |
| GitHub Actions | YAML schema validated; five jobs prepared, no remote run |

E2E covers keyboard login → reviewed evidence → verified fact → profile publication → import → requirement review → fact-based assessment → score/coverage → opening snapshot evidence → shortlist → confirmed manual submission record → export → logout. It checks that imported scripts do not execute and that there are no JavaScript errors or horizontal overflow. The database is `jobhunter_test_e2e`, with synthetic data.

Startup from scratch was verified in a separate Compose project with its own ports and volume, removed on completion. The personal volume was preserved. In API tests, an injected audit failure proved rollback; audit UPDATE/DELETE/TRUNCATE and snapshot modifications were denied to the runtime role.

## Known limitations

- The Playwright Chromium download timed out; the already installed official Edge channel was used. The Linux workflow is configured for Chromium. That workflow was not run remotely.
- There are two upstream deprecation warnings in the Starlette/httpx and AnyIO test client. They remain visible and are not test failures.
- The public dataset is not a human gold set and does not contain the private factual profile. Its execution preserved conservative controls but produced disagreements requiring review; [details](evaluation-results.md).
- This phase has no automatic private CV import, semantic parser, package generation, submission, AI provider or cloud resources.

Reproducible commands: [local development](../local-development.md). Browser automation sources: [Playwright webServer](https://playwright.dev/docs/test-webserver) and [CI](https://playwright.dev/docs/ci).
