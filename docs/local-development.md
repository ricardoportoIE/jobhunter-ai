# Local development — P1, P2 and P3

The core includes login, a factual profile, evidence, vacancy review, deterministic matching,
an Inbox, a manual tracker and export. P2 adds explicitly requested AI calls and semantic search.
See [P2 configuration, privacy, costs and benchmark](phase-2/operations.md).
P3 adds strategy, documents and approval: [operation](phase-3/operations.md)
and [validation](phase-3/validation.md). `python-docx` and ReportLab are in the API lockfile;
Word and LibreOffice are not required to run the application.
AWS and submission channels remain outside the current runtime.

## Prerequisites

Docker Desktop with Linux containers and Compose supporting `--wait`; Python and uv 0.12.7. Frontend development and E2E testing require Node 24 and npm. The API uses Python 3.13; `uv sync` installs the selected version when required.

## Start

From the repository root:

```powershell
python scripts/init_env.py
docker compose config --quiet
docker compose up --build --detach --wait --wait-timeout 120
uv sync --project apps/api --locked
uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap
python scripts/smoke_local.py
```

Open http://127.0.0.1:5173. Sign in as `local` using the password in `.private/local-login.txt`. Bootstrap preserves an existing account. `.env` contains separate administrative and runtime credentials; the initialiser preserves existing values and adds the runtime credential to older installations. Do not print or publish `.env`.

Compose starts PostgreSQL, runs migrations/grants in the temporary `migrate` service, and starts the API/web after health checks. It is normal for `migrate` to finish with exit code 0. The API and web run without root, with read-only filesystems and temporary `/tmp` storage. Compose does not pass the administrative password to the runtime.

| Service | Default address |
|---|---|
| Application | http://127.0.0.1:5173 |
| API documentation | http://127.0.0.1:5173/api/docs |
| Direct API | http://127.0.0.1:8000 |
| PostgreSQL | `127.0.0.1:5433` |

All ports bind to loopback. `WEB_PORT`, `API_PORT` and `JOBHUNTER_DB_PORT` in `.env` allow occupied ports to be changed. Compose adjusts the allowed origins to the web port. Swagger uses its default CDN assets; the application uses local assets.

```powershell
docker compose ps
docker compose logs --tail 80 api web migrate
docker compose down
```

`down` preserves the database. **Do not use `down --volumes` for a normal shutdown**, because it erases the data. Editing passwords in `.env` does not automatically change passwords already stored in PostgreSQL.

## First workflow

1. In the profile and evidence screen, record evidence and confirm its review.
2. Record a fact with evidence, the `matching` use and explicit review; publish the profile version.
3. Import vacancy text and confirm its fields and requirements.
4. Assess requirements using reasons and valid facts. Consider score and coverage together.
5. Open the result's evidence; add the vacancy to the shortlist and track it in applications.
6. Record a submission only if you have already made it outside the application, with a date, channel and reference.

Alternatively, the following command creates a **fictitious profile** and refuses to run if the profile already has facts. Do not use it to mix fictitious data with your real profile:

```powershell
uv run --project apps/api --env-file .env python -m jobhunter_api.manage seed
```

The phase 0 CV and private facts were not imported automatically. See [runtime contracts and decisions](phase-1/runtime-contracts.md).

## Automatic reload

```powershell
docker compose stop api web
docker compose up --detach --wait db
uv run --project apps/api --env-file .env python -m jobhunter_api.manage provision
uv run --project apps/api --env-file .env uvicorn jobhunter_api.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

In another terminal:

```powershell
cd apps/web
npm ci
npm run dev
```

Vite uses port 5173 and proxies `/api` to 8000. If you change the API port, set `API_PROXY_TARGET` in the Vite terminal. If you change the Vite port, set `JOBHUNTER_ALLOWED_ORIGINS` to a JSON list in the API environment. Never pass a password as a command-line argument.

## Tests and checks

For the API, from `apps/api`, with PostgreSQL running:

```powershell
uv sync --locked
uv run --locked ruff check . ../../scripts/init_env.py ../../scripts/smoke_local.py ../../scripts/evaluate_phase1.py
uv run --locked ruff format --check . ../../scripts/init_env.py ../../scripts/smoke_local.py ../../scripts/evaluate_phase1.py
uv run --locked mypy
$env:JOBHUNTER_TEST_DB_NAME='jobhunter_test'
uv run --locked --env-file ../../.env pytest
uv run --locked python ../../scripts/evaluate_phase1.py --check
uv build
```

In a POSIX shell, use `export JOBHUNTER_TEST_DB_NAME=jobhunter_test` instead of the PowerShell assignment. Integration tests use a separate database and refuse names without the `jobhunter_test` prefix. Without the variable, PostgreSQL tests are skipped; this does not count as full validation. Two deprecation warnings from the Starlette/httpx client and AnyIO remain visible.

For the frontend, from `apps/web`:

```powershell
npm ci
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

E2E testing creates only `jobhunter_test_e2e`, uses fictitious credentials and temporary servers on ports 5174/8001, and does not reuse the personal application. It follows profile → import → review → matching → evidence → tracker → export on desktop and mobile. On Windows, if Chromium cannot be downloaded and Edge is already installed:

```powershell
$env:PLAYWRIGHT_CHANNEL='msedge'
npm run test:e2e
```

Screenshots/traces are saved in `apps/web/test-results/` and the report in `apps/web/playwright-report/`; Git ignores both. The frontend uses Prettier (`npm run format`), ESLint and strict TypeScript.

The guided design journey also checks combined vacancy filters, compact navigation,
layout at 320 pixels and axe accessibility rules on the principal screens. See the
[frontend experience](frontend-experience.md) for the interaction changes and test scope.

From the root, with Compose running:

```powershell
python scripts/smoke_local.py
python scripts/smoke_local.py --exercise-db-recovery
python scripts/check_documentation.py
```

The second command briefly stops this project's `db`, verifies liveness 200/readiness 503, and restarts it in `finally` without deleting data. `--web-url`/`--api-url` allow different ports. The five CI jobs cover the API, frontend, Compose, browser E2E and design contracts. The workflow runs on pushes and pull requests; see [GitHub Actions](https://github.com/ricardoportoIE/jobhunter-ai/actions/workflows/ci.yml) for its current status.

## Privacy

Export data from the privacy screen. Complete application data erasure is an administrative command requiring explicit confirmation; see [security and data](phase-1/security-and-data.md). There is no submission endpoint, remote collection or `.private/` mount in the containers. Private backups and exports must not enter Git.
