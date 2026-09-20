# P4 — Discover and review opportunities

P4 adds a local discovery worker, the public Greenhouse Job Board reader and optional
read-only Gmail alerts. It keeps the existing review, matching and application package
workflow. It does not apply for jobs or send email.

## Everyday use

1. Open **Opportunities → Discover opportunities → Manage sources**.
2. Add a Greenhouse board token and a recognisable source name. For Gmail, follow
   [Gmail setup](gmail-setup.md), connect the account and choose a custom alerts label.
3. Record the applicable terms or permission reference, the purpose of the read and
   an access-review expiry within 90 days. Confirm the review and enable daily checks.
4. Use **Check now** for the first read, or leave the Docker stack running. The worker
   selects one due source each minute. **Pause source** stops subsequent checks.
5. Filter discoveries by source or text, and optionally show only unseen updates.
   Dismiss irrelevant items; **Show dismissed items** provides restoration.
6. **Save and review vacancy** creates an unreviewed job and opens its review screen.
   Explicitly request AI extraction if useful, check the fields and assess requirements.
   Imported API fields are provider statements, not verified candidate eligibility.

Email digests remain alerts because one message may contain several jobs. Expand the
source text and choose one link; it populates the import form without fetching the
destination or granting AI consent. Attachments are ignored. OAuth access is broader
than a label, so the app enforces the dedicated-label restriction itself.

The interface defaults to English (UK) and preserves Portuguese as an optional
translation. Original adverts, email subjects and candidate text retain their language.

## Source updates and reliability

New/changed items retain the source ID, external ID, URL, content hash and observation
times. The source's supplied update timestamp remains separate from retrieval time.
Conditional GETs preserve cache validators. A complete board can mark a previously
listed post as **not listed**; a failed or incomplete response never does so. This
status is not a confirmed closure and does not create an automatic eligibility blocker.

A changed advert never silently overwrites a reviewed vacancy. The job screen warns
about the pending update. **Compare with the saved review** shows the earlier text.
After explicit confirmation, **Apply update and review again** preserves that earlier
version, replaces the advert, clears extracted fields and requires review again.
Expected versions prevent applying a stale comparison; identity conflicts require
manual resolution. New URLs are registered for subsequent deduplication.

Pending content changes prevent new matching and strategy generation and mark old
matches/packages stale. Existing version checks also protect later approval/download
after an update is applied. Absence from a board alone remains an uncertainty to
check with the employer. Downloads outside the application are not updated automatically.

Preference hints are exact text mentions of target roles and locations. They are
not a suitability score, semantic ranking or assertion that requirements are met.
The existing matching model and deterministic rules remain responsible for assessment.
The company-research shortcut prepares a question only; select official source domains
and explicitly authorise the existing cited web-search operation before it runs.

## Runtime and recovery

Migration 007 adds indexes and a separate OAuth secret table. Existing migrations and
candidate records are preserved. Compose's `migrate` service reapplies runtime grants.
The `discovery` service shares the API image but has no OpenAI key, public port or
administrative database credential. It runs without root on a read-only filesystem.

```powershell
docker compose up --build --detach --wait --wait-timeout 120
docker compose ps
docker compose logs --tail 50 discovery
```

Successful batches wait one day. Failed batches wait at least 15 minutes, or longer
when Retry-After requires it. Access denial pauses the source. A global PostgreSQL
session lock serialises connector batches; a five-minute lease records interrupted
work. An expired lease is replaced on the next due check, with the previous run marked
interrupted. A configuration change during a read cancels its results. An old failure
cannot overwrite a newly reviewed connection's settings.

The worker heartbeat is written only after a successful scheduler tick. Compose marks
it unhealthy if it stops making progress for 180 seconds. A source-level failure is
recorded in source history and does not crash the worker. Database failures are retried
without logging credentials or source text. Startup is inert until a source is enabled.

Greenhouse reads use its fixed HTTPS API host, up to 500 posts and 4 MiB per response.
Malformed or incomplete boards fail atomically. Public destinations are DNS-validated
and pinned for TLS connections; redirects are rejected. Reads have bounded deadlines
and at most two transient retries. Gmail additionally limits each batch to 60 seconds
and at most 40 unique messages; expired pagination cursors reset on the next retry.
The application neither bypasses access restrictions nor polls arbitrary website URLs.

For local development without Docker's worker:

```powershell
uv run --project apps/api --env-file .env python -m jobhunter_api.discovery_worker
```

Use only one intended environment. The database lock prevents simultaneous provider
batches even if an API request and worker overlap. A sleeping/offline computer does
not collect opportunities. This is a bounded personal pilot, not continuous hosted
monitoring, a full internet search or a complete historical mailbox synchronisation.

## Privacy and retention

Imported discovery data, source reviews, run history and old advert snapshots are
private local records. They remain until explicit local erasure; the UI shows only
the most recent 30 runs per source. **Dismiss** and **Disconnect** do not erase history.
The existing private export includes these records, but excludes encrypted OAuth
tokens and transient OAuth state. See [privacy and erasure](../phase-1/security-and-data.md).

Tokens are encrypted with a separate Fernet key in ignored backend configuration.
Neither plaintext credentials nor ciphertext belong in ordinary records, snapshots,
exports or frontend assets. Google revocation is attempted on disconnect; its outcome
is shown separately from successful local credential removal. Back up credentials
and exports privately, and revoke Google access before full local erasure when possible.

## Validation boundaries

See [delivery progress](progress.md) and [final validation](validation.md). Greenhouse
has a recorded live public-read probe. Gmail is implemented and exercised with synthetic
OAuth/provider responses in API and browser tests; a live account connection awaits
the operator's Google client. No Google application verification or platform-wide
collection permission is claimed. Confirm the actual source's access basis before
enabling recurring reads.
