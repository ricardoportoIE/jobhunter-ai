# JobHunter AI

A career intelligence platform that compares vacancies against an evidence-based profile and prepares applications for human review.

**Status: P1, P2 and P3 are complete for local use with human review.** Features include AI extraction with citations, embeddings, semantic search, assisted matching and application packages with strategy, CV/cover letter DOCX/PDF files, answers, evidence, history and approval. Matching uses Luna high, clarification gates and cited public research. Live GPT-4.1 mini and Luna tests, their results and limitations are documented. Project limits: €10/month for AI and €25 combined.

## Start locally

The interface defaults to **English (UK)**, with a persistent Portuguese option.
Start a profile from a PDF/Word CV draft or import a public vacancy link, then review
the extracted information before applying it. See [CV imports, vacancy links and languages](docs/imports-and-languages.md).

With Docker Desktop in Linux mode, Python and uv 0.12.7, run from the repository root:

```powershell
python scripts/init_env.py
docker compose up --build --detach --wait --wait-timeout 120
uv sync --project apps/api --locked
uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap
python scripts/smoke_local.py
```

Open [the application](http://127.0.0.1:5173). The username is `local`; the initial login password is in `.private/local-login.txt`. Database credentials are in `.env`. Both files are ignored by Git. To stop the application while retaining the database, run `docker compose down`.

See [development and testing](docs/local-development.md), [delivery by stage](docs/phase-1/progress.md), [runtime contracts](docs/phase-1/runtime-contracts.md), [the 20-case evaluation](docs/phase-1/evaluation-results.md) and [privacy and erasure](docs/phase-1/security-and-data.md).

For AI features, see [P2 operation and privacy](docs/phase-2/operations.md),
[stages and commits](docs/phase-2/progress.md) and [validation and evaluation limitations](docs/phase-2/validation.md).
Configure the key only in the backend's `.env`, using `python scripts/configure_openai.py FILE_PATH`.
Then recreate the API with `docker compose up --detach --wait api`.

To generate documents, open a reviewed vacancy and select the fourth tab, the application package.
See [P3 operation](docs/phase-3/operations.md), [stages and commits](docs/phase-3/progress.md)
and [live tests and visual verification](docs/phase-3/validation.md).

Selection by reliability: [live GPT-4.1 mini versus GPT-5.6 Luna comparison](docs/evals/model-comparison.md).
Local matching now uses **Luna high**, with clarifications, a second assessment and cited public
research. See [implementation, new live tests, user labels and limitations](docs/evals/luna-migration.md).

## Start with phase 0

1. [Product, scope and metrics](docs/phase-0/product-brief.md)
2. [Completion and exit criteria](docs/phase-0/discovery.md)
3. [Candidate Knowledge Base and master CV](docs/phase-0/candidate-knowledge-base.md)
4. [Vacancy sources and evaluation dataset](docs/phase-0/sources-and-evaluation.md)
5. [Architecture and states](docs/architecture/overview.md)
6. [Data contracts](schemas/README.md)
7. [Threat model](docs/security/threat-model.md)
8. [Wireframes for the four initial screens](docs/phase-0/wireframes.md)
9. [Cost estimate](docs/phase-0/costs.md)
10. [Prioritised phase 1 backlog](docs/phase-0/backlog.md)
11. [Matching and permission-to-start policy](docs/phase-0/matching-policy.md)
12. [Real dataset and evaluation limitations](docs/phase-0/evaluation-report.md)

## Architecture decisions

- [ADR-001: monorepo and modular monolith](docs/adr/0001-modular-monolith.md)
- [ADR-002: AI, Bedrock, AgentCore and alternatives](docs/adr/0002-ai-runtime.md)
- [ADR-003: evidence, scoring and approval](docs/adr/0003-evidence-and-approval.md)
- [ADR-004: budget and temporary AWS environments](docs/adr/0004-local-first-budget.md)

Implemented workflow: record evidence and facts, publish the profile, import vacancy text, confirm requirements, review matching, prepare a strategy and documents, review answers/differences, approve the package and track a manual application. Score calculation remains deterministic.

## Data and validation

Examples in `data/fixtures/` are fictitious. `data/evals/real-cases.json` contains 20 paraphrased, pseudonymised real advertisements with assistant-authored design labels; it is not a human gold set. Live results are in `data/evals/phase2-benchmark.json`. The CV, 114 facts, 43 evidence records, contacts, constraints and original advertisements are in `.private/`, which Git ignores.

Documentation and schema validation:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-phase0.txt
.venv\Scripts\python scripts/validate_phase0.py
.venv\Scripts\python scripts/validate_phase0.py --private
python scripts/check_documentation.py
```

The `--private` command also validates private data on this machine and does not apply to clones without `.private/`. Application tests are described in the development guide. No cloud deployment, AWS resources, email integration or application submission channel is configured. P2 was validated with active billing; each vacancy still requires human review before scoring. Calibration with new human labels belongs to the pilot.

## Documentation language

All authored project documentation uses **British English (en-GB)**. Follow [the project conventions](AGENTS.md)
and [the documentation review policy](docs/documentation-policy.md), including the final language and link check.
