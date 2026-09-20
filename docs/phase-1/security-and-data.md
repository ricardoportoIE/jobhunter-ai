# Phase 1 security and data

The runtime uses `jobhunter_app`, without superuser, CREATE DATABASE, CREATE ROLE or CREATE on the schema. The ephemeral `migrate` service uses the administrative credential only for migrations and grants, and exits before the API starts. The API receives only the runtime credential in Compose. Outside Docker, `Settings.runtime()` selects `JOBHUNTER_APP_DB_PASSWORD` from `.env`.

Audit records and snapshots allow SELECT/INSERT for the runtime; UPDATE, DELETE, TRUNCATE and DDL are denied. This protects against the application, not the PostgreSQL administrator. Each mutation and its event are written in the same transaction. Writes are serialised per owner using an advisory lock and optimistic versions; the application index also prevents duplicates in the database.

Sessions use random opaque tokens hashed in the database, an HttpOnly/SameSite Strict cookie, an absolute eight-hour expiry, logout with revocation and CSRF + allowed-origin checks on writes. Local HTTP uses a cookie without Secure; a future HTTPS deployment must enable `JOBHUNTER_COOKIE_SECURE=true` and define explicit origins. No public access is configured.

Imported text, sources and explanations are data. No URL triggers server-side fetching; the interface uses React escaping and never injects raw HTML. Total body limit: 128 KiB; advert: 50,000 characters. Private responses have `Cache-Control: no-store`. Access logs containing query strings were disabled in Nginx/uvicorn; unexpected errors record only correlation and type, without the original exception, SQL or body.

## Export

On the privacy screen, the export download action retrieves authenticated JSON containing records, snapshots and audit history. It excludes password hashes, cookies, session tokens and CSRF tokens. The file contains personal data if any has been entered; keep it outside Git. The endpoint is `GET /api/v1/candidate/export`.

## Administrative erasure

Deleting a fact/evidence record through the interface is a soft deletion: history remains available and analyses become stale. To erase application data, including snapshots, history, idempotency keys and sessions, run this from the root **only when you intend that erasure**:

```powershell
uv run --project apps/api --env-file .env python -m jobhunter_api.manage erase --confirm DELETE_LOCAL_APPLICATION_DATA
```

The local account and its password hash are preserved so that you can log in again. This command does not delete source files in `.private/`, exports or external backups; they are outside the application database. Delete those copies separately if intended. No real data was erased during development: the test uses an isolated database with synthetic data.

Old copies remain in backups until deleted; restoration must respect subsequent erasure requests. Automated recovery and backups belong to phase 5.
