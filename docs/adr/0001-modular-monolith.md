# ADR-001 — Monorepo and modular monolith

Status: adopted as the phase 1 baseline. Date: 2026-09-19.

## Context

One developer, one user and a small initial workflow need contracts and the interface to evolve together. The brief describes many logical services, but these do not require separate processes.

## Decision

Use a monorepo with a modular FastAPI backend, React/TypeScript frontend and PostgreSQL. Keep the domain separate from adapters. Create packages only when they have an implemented responsibility; do not copy the entire future directory tree from the brief.

## Alternatives

| Alternative | Benefit | Cost at this stage |
|---|---|---|
| Monolith without modules | Less initial structure | Rules, infrastructure and the provider become intertwined |
| Selected modular monolith | Simple transactions, coordinated contracts, small deployment | Requires dependency discipline |
| Microservices | Independent deployment and scaling | Networking, distributed observability and consistency before they are needed |
| Separate repositories | Team autonomy | There are no independent teams; contract changes become harder |

## Consequences and review

Modules share a database, accessed through their own services/repositories. Heavy rendering and ingestion may become workers using the same domain. Extract a service only when measured security isolation, load or deployment requirements justify it. The first phase does not install LangGraph, Redis, Celery, MCP or pgvector.

P1-01 implements `apps/api` (Python 3.13, FastAPI, psycopg) and `apps/web` (Node 24, React 19, TypeScript 6, Vite 8), with PostgreSQL 17. TypeScript 6 is within the range supported by the selected typescript-eslint version. `uv.lock` and `package-lock.json` pin resolved dependencies; Docker images and CI actions use digests/SHAs. The API's Python environment is separate from the phase 0 documentation validator.

In this increment, the API contains only configuration, database connectivity and health checks. There are no domain tables, migrations or private data imports. The frontend accesses `/api` on the same origin: Nginx in Compose and the Vite proxy in development mode. Published ports bind to `127.0.0.1`; a random credential is stored in the ignored `.env` file. See [local development](../local-development.md) for operational details.
