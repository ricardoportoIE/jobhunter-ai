# P1-01 — Structure and local environment

Status: implemented and verified locally on 2026-09-19. Phase 1 continues with P1-02.

| Criterion | Implementation / evidence |
|---|---|
| Monorepo and architecture | `apps/api` and `apps/web`; ADR-001 updated; no empty modules for future features |
| Compose with health checks | PostgreSQL, API and Nginx started and healthy; API readiness runs `SELECT 1` |
| Configuration without secrets in code | `.env.example` with a blank password; initialiser generates a random password without overwriting `.env` |
| Versions and lockfiles | Python 3.13, Node 24; `uv.lock`, `package-lock.json`; images pinned by digest and CI actions by SHA |
| Lint, types, tests, builds | Ruff, mypy, pytest; ESLint, TypeScript, Vitest; API wheel/sdist and Vite build |
| CI | Workflow with four jobs; commands run locally, not yet run on GitHub |
| Local ports | Published on `127.0.0.1` at default ports 5173, 8000 and 5433 |
| Private data | `.private/` and `.env` ignored by Git; allowlisted builds and restricted contexts |

## Checks performed

- API: 6 tests passed, covering database-independent liveness, readiness 200/503, credential redaction and invalid configuration. Ruff/format and mypy passed; wheel/sdist generated.
- Web: 4 tests passed, covering success, HTTP error with retry, invalid response and network failure. ESLint, TypeScript and production build passed. The npm installation reported no vulnerabilities at that time.
- Compose: both images built and three services healthy. Smoke tests check the frontend, assets, direct and proxied API, OpenAPI and Swagger. Database stopped and recovered with liveness 200, readiness 503 during the outage and a return to 200 without restarting the API/web app.
- Phase 0 public contracts: validator passed, including 15 rejection cases and the 20 derived real-world cases. This does not run the future matching algorithm.
- Git initialised locally; `.env`, `.private/` and local dependencies confirmed as ignored. No commit, remote or publication.

## Validation limitations

The automation browser was unavailable; there was no visual inspection or E2E test in a real browser. Component tests ran in jsdom and HTTP smoke tests against the real containers. The workflow did not run on GitHub because no remote is configured.

Pytest emits two deprecation warnings from the Starlette/httpx and AnyIO test dependencies; tests pass and warnings remain visible. Review these dependencies when updating the lockfile.

There is no authentication, private data in the application, domain tables, migrations, AI integration, AWS resources or application submission. These features have their own backlog items.

Operations and reproducible commands: [local development](../local-development.md).
