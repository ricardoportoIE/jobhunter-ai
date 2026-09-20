# JobHunter AI

**An evidence-led career assistant that helps people decide which vacancies to pursue and prepare applications they can stand behind.**

Job searching involves more than matching keywords. A useful decision needs to account for experience, evidence, missing information and requirements that cannot be negotiated. JobHunter AI brings these into one reviewable workflow: build a factual profile, assess a vacancy, prepare an application and track the outcome.

This portfolio project demonstrates full-stack development, applied AI, data modelling, security and automated testing through a working local application. Its central engineering principle is simple: **AI proposes; verifiable rules and human review control what becomes an accepted fact, a score or an approved document.**

**Available now:** a Docker-based local application with profile and vacancy imports, evidence-backed matching, application documents and a manual tracker. The interface defaults to English (UK), with a persistent Portuguese option. All authored project documentation is in British English.

## The user journey

1. **Build a profile.** Upload a PDF, DOCX or Markdown CV, or enter information manually. AI creates an editable draft; the user can add, change or remove facts and evidence before confirming them.
2. **Understand a vacancy.** Import a public HTTPS link or paste the advertisement. Review the extracted role, requirements and source text before continuing.
3. **Assess the fit.** Examine each requirement against approved evidence. The application shows a deterministic score, evidence coverage, explicit blockers and questions that still need clarification.
4. **Prepare an application.** Review an AI-assisted strategy, select supported facts and generate CV and cover letter documents in DOCX/PDF. Check answers, differences and evidence before approving a specific package version.
5. **Track the outcome.** Shortlist vacancies and record applications, interviews and outcomes. Submission takes place outside the application and is recorded explicitly by the user.

The workflow preserves drafts and form input, explains review requirements and guides the user to the next step. Desktop and mobile browser tests exercise both the successful journey and recovery from errors.

## Engineering skills demonstrated

| Area | Technologies and skills | How they are applied |
|---|---|---|
| Frontend engineering | React 19, TypeScript 6, Vite 8, CSS, internationalisation | Responsive screens, typed API calls, editable drafts, keyboard navigation, translated feedback and persistent language selection. |
| Backend engineering | Python 3.13, FastAPI, Pydantic, REST APIs | Validated contracts, authentication, domain services, explicit workflow transitions and consistent error responses. |
| Data engineering | PostgreSQL 17, SQL migrations, psycopg, JSONB | Versioned records, transactional audit events, ownership boundaries, evidence relationships and conflict detection. |
| Applied AI | OpenAI Responses API, structured outputs, embeddings, semantic retrieval | CV and vacancy extraction, cited matching, fact selection, second assessments and explicitly requested public web research. |
| Reliability and evaluation | Deterministic rules, contract validation, frozen evaluation sets | Reproducible scoring, source checks, clarification gates, disagreement handling and recorded model comparisons with stated limitations. |
| Security and privacy | Argon2, session cookies, CSRF protection, authorisation, SSRF controls | User isolation, protected writes, restricted public URL fetching, bounded document parsing and backend-only credentials. |
| Document processing | pypdf, python-docx, ReportLab | Importing source material and producing reviewable DOCX/PDF documents from approved facts. |
| Quality assurance | pytest, Vitest, Testing Library, Playwright | Domain, API, database, component and browser tests, including failure recovery and desktop/mobile journeys. |
| Developer tooling and delivery | Docker Compose, Nginx, GitHub Actions, uv, npm, Ruff, mypy, ESLint, Prettier | Reproducible environments, locked dependencies, static analysis, production builds, health checks and continuous integration. |
| Product and architecture | Modular monolith, threat modelling, architecture decision records | A scoped product, documented trade-offs, reviewable decisions and a clear separation between implemented features and future plans. |

For a focused code review, start with the [scoring engine](apps/api/src/jobhunter_api/scoring.py), [AI validation](apps/api/src/jobhunter_api/ai_matching.py), [CV import](apps/api/src/jobhunter_api/cv_import.py), [public URL reader](apps/api/src/jobhunter_api/job_url.py) and [browser journeys](apps/web/e2e).

## How reliability is built in

- **Evidence before claims.** Facts retain their source, review status, permitted uses and validity. CV excerpts are resolved from validated source ranges; generated documents use approved facts.
- **Rules own the decision boundaries.** Code calculates weights and scores. Desirable skills cannot compensate for an explicit disqualifier, and permission to pursue an offer remains separate from permission to start employment.
- **Uncertainty remains visible.** Missing decisive information, conflicting evidence and title/body disagreements require clarification. Different assessments are preserved for review rather than silently selecting the most favourable result.
- **Approval belongs to a version.** Changes to source information invalidate affected approvals. A previously approved package is not treated as current after its supporting evidence changes.
- **AI calls are accountable.** A cost ledger reserves and settles usage, caches equivalent requests and blocks further calls when unresolved usage requires reconciliation. Model, reasoning effort and prompt settings are configurable by task within a validated catalogue.
- **External content is untrusted.** Document parsing has size, time and resource limits. URL imports check destinations and redirects, respect source restrictions and do not bypass authentication or CAPTCHAs.

The project includes [model comparison evidence](docs/evals/model-comparison.md) and [subsequent workflow evaluations](docs/evals/luna-migration.md). These are small, recorded experiments, including synthetic cases and historical vacancy snapshots. They do not establish general model superiority or predict hiring outcomes; failures and label limitations remain in the reports.

## Architecture

The application is a **modular monolith**: one API, one database and explicit boundaries between the browser, domain rules and external services. This keeps local development practical while making the important decisions independently testable.

```mermaid
flowchart LR
    User[User] --> Web[React and TypeScript]
    Web --> Proxy[Nginx]
    Proxy --> API[FastAPI]
    API --> Domain[Profiles, evidence, matching and packages]
    Domain --> DB[(PostgreSQL)]
    Domain --> Rules[Deterministic scoring and validation]
    API --> AI[Budgeted AI adapter]
    AI --> Provider[OpenAI API]
    API --> Import[Bounded document and public URL import]
    Domain --> Documents[DOCX and PDF rendering]
```

The browser never receives the provider key or database credentials. Local services bind to loopback. The API and web containers run without root; the runtime database account is separate from the administrative account. AI features send the context needed for the requested task to the configured provider, so local hosting does not mean that AI processing is offline.

```text
apps/api/       FastAPI application, domain logic, migrations and tests
apps/web/       React application, component tests and browser journeys
data/          Synthetic fixtures and recorded evaluation artefacts
docs/          Product decisions, architecture, operations and validation
schemas/       Design-time data contracts
scripts/       Setup, health checks, evaluation and documentation validation
.github/       Continuous integration workflow
```

## Run locally

### Prerequisites

- Docker Desktop using Linux containers, with Docker Compose supporting `--wait`.
- Python and uv **0.12.7**. The API uses Python **3.13**, which uv can install when needed.
- Node.js **24** and npm for frontend development and browser tests; they are not required on the host for the Docker-based application.
- An OpenAI API key with billing and access to the configured models for AI features. The manual workflow can run without a key.

From the repository root, run:

```powershell
python scripts/init_env.py
docker compose up --build --detach --wait --wait-timeout 120
uv sync --project apps/api --locked
uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap
python scripts/smoke_local.py
```

Open **http://127.0.0.1:5173** and sign in as `local` using the generated password in `.private/local-login.txt`. API documentation is available at **http://127.0.0.1:5173/api/docs**. The initialiser preserves existing configuration and bootstrap preserves an existing account.

To enable AI, import a key from a local file; replace `PATH_TO_KEY_FILE` with its path:

```powershell
python scripts/configure_openai.py PATH_TO_KEY_FILE
docker compose up --detach --wait api
```

Keys stay in the backend configuration. `.env`, `.private/`, local exports and source CVs must stay outside version control. The default project limits are **EUR 10 per month for AI** and **EUR 25 combined**; these are application settings, not a guarantee about provider billing. Check [AI configuration and operations](docs/phase-2/operations.md) and [task-specific model settings](docs/evals/luna-migration.md) before changing providers or models. Model access depends on the API account.

Stop the application with `docker compose down`; this retains the database. See the [development guide](docs/local-development.md) for automatic reload, alternative ports, synthetic seed data and troubleshooting.

## Testing and validation

The [GitHub Actions workflow](.github/workflows/ci.yml) defines five jobs: API, frontend, Docker Compose, browser end-to-end tests and design contracts. It checks formatting, types, application behaviour, evaluation contracts, builds and database outage recovery. Automated tests use synthetic data; recorded live AI results are validated without making paid calls in CI.

Local verification on **20 September 2026** passed **113 API tests, 18 frontend tests and 10 desktop/mobile browser tests**, with no skipped API tests. Static checks, package and frontend builds, evaluation contracts, documentation checks and database outage/recovery checks also passed. Two upstream Python deprecation warnings remain; browser tests used Microsoft Edge.

Run the API tests against a separate test database, with the local PostgreSQL service running:

```powershell
$env:JOBHUNTER_TEST_DB_NAME='jobhunter_test'
uv run --project apps/api --locked --env-file .env pytest apps/api/tests
```

Run frontend and browser tests:

```powershell
cd apps/web
npm ci
npm test
npx playwright install chromium
npm run test:e2e
```

On Windows, an installed Microsoft Edge can be used by setting `$env:PLAYWRIGHT_CHANNEL='msedge'` before `npm run test:e2e`. Browser tests use disposable test data and their own application servers.

From the repository root, validate the design contracts and documentation:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-phase0.txt
.venv\Scripts\python scripts/validate_phase0.py
python scripts/check_documentation.py
```

The [development guide](docs/local-development.md) lists the lint, type, build and recovery commands; the workflow is the complete CI checklist. PostgreSQL tests skipped because no test database was configured do not count as a full pass. Live model probes are separate, explicit operations described in the evaluation guides.

## Project scope and next steps

The local core, AI assistance and application package workflow are implemented. The project currently supports individual use with human review. There is no hosted production service, email integration or automated application submission.

Further work includes broader user-labelled evaluations, testing with more document layouts and sources, and a carefully scoped pilot. The planned stages extend the engineering skills above:

| Planned stage | Skills and technologies to develop | Intended purpose |
|---|---|---|
| Discovery | Opt-in email integration, permitted APIs, source provenance and alerts | Bring traceable opportunities into the review workflow. |
| Temporary AWS demonstration | Terraform, IAM, Secrets Manager, Cognito, API Gateway, Lambda, ECS Fargate, RDS, S3, EventBridge, Step Functions and observability | Validate reproducible deployment, access controls, backups, cost monitoring and clean-up. The topology remains subject to budget and design validation. |
| Controlled orchestration | Resumable workflows, idempotent integrations and scoped approval; LangGraph or MCP only where justified | Test one permitted channel or sandbox with final confirmation and auditable outcomes. |

These are future plans, not deployed capabilities. Bedrock is an inference option for the cloud pilot; AgentCore remains deferred until a measured requirement justifies it. Everyday use remains local, and temporary cloud environments must fit the project's cost constraints. See the [product brief](docs/phase-0/product-brief.md), [architecture](docs/architecture/overview.md) and [runtime decision](docs/adr/0002-ai-runtime.md) for the reasoning behind this scope.

## Explore the project

| If you want to understand… | Start here |
|---|---|
| The product and its users | [Product brief](docs/phase-0/product-brief.md) |
| Imports, draft review and languages | [User workflow guide](docs/imports-and-languages.md) |
| Architecture and design trade-offs | [Architecture](docs/architecture/overview.md) · [AI runtime decision](docs/adr/0002-ai-runtime.md) · [Evidence and approval](docs/adr/0003-evidence-and-approval.md) |
| Security, ownership and personal data | [Threat model](docs/security/threat-model.md) · [Privacy and erasure](docs/phase-1/security-and-data.md) |
| AI quality, costs and limitations | [AI operations](docs/phase-2/operations.md) · [Evaluation results](docs/phase-2/validation.md) · [Model migration evidence](docs/evals/luna-migration.md) |
| Application documents and approval | [Package workflow](docs/phase-3/operations.md) · [Validation and visual checks](docs/phase-3/validation.md) |
| Development and documentation conventions | [Local development](docs/local-development.md) · [Documentation policy](docs/documentation-policy.md) · [Project conventions](AGENTS.md) |

Public fixtures are fictitious. Real-vacancy evaluation cases are paraphrased and pseudonymised; their design labels are not a complete human gold set. Personal CVs, contact details, original private evidence and credentials are excluded from the repository.
