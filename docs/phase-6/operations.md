# P6 — Local application rehearsal

P6 adds a final review and a resumable submission workflow using one **local sandbox**.
No employer, Gmail account, job board or cloud service receives a submission. The
sandbox stores a receipt in PostgreSQL and leaves the real application status unchanged.
The existing manual tracker still records applications made outside JobHunter.

## Start and review

Use the normal [local setup](../local-development.md). Rebuilding Compose applies
migration `008_submissions.sql`; no new secret, paid model call or AWS resource is needed.

1. Review the profile, vacancy and deterministic analysis. Resolve application blockers
   and outstanding clarifications. A condition to review before starting work remains
   separate from the decision to pursue an application.
2. Generate and approve the current document package. From the package, select
   **Continue to application rehearsal**, or open **Applications → Rehearse application**.
3. Choose an approved package and select **Prepare final review**. Review the name,
   contacts, CV claims, cover letter claims and answers that appear. The recipient is
   always the local sandbox. Source evidence and internal AI reasoning are excluded
   from this payload; the approved package digest is retained for verification.
4. Tick the specific simulation confirmation and select **Authorise rehearsal**.
   This approval lasts 15 minutes and is separate from document approval. Select
   **Run local rehearsal**, or **Cancel rehearsal** before execution.
5. A successful attempt shows a **Simulated receipt**, with its identifier and time.
   The tracker records a simulation event; it does not record a real submission.

The interface is available in English (UK) and Portuguese. Vacancy text, evidence and
personal document content retain their original language.

## Recovery and changed information

Closing the tab or restarting the API does not discard the checkpoint. Reopen the
application's rehearsal to read its saved state. **Refresh rehearsal** is a read-only
recovery action. After a lost write response, the interface requires a refresh before
another action; it never automatically retries execution.

| Saved state | Next action |
|---|---|
| `NEEDS_REVIEW` | Review and explicitly authorise the displayed content |
| `APPROVED` | Run, cancel or renew authorisation after reviewing again |
| `DISPATCHING` or `UNKNOWN` | Select **Check attempt result**; do not resend |
| `FAILED` | The local receiver definitively has no receipt; review and authorise again |
| `CANCELLED` | Prepare a new review before authorising |
| `SIMULATED` | Inspect the receipt; further execution returns the same completed result |

If the receiver lookup fails, the attempt remains unresolved. A definitive absence
closes the attempt under the same lock used for acceptance, so a delayed request
cannot subsequently accept it. A received acknowledgement must match the attempt and
payload digest. A mismatch remains pending for investigation.

Profile, vacancy, evidence, package and analysis changes are checked again at approval,
execution and receiver acceptance. Expired facts and changed or missing discovery
sources block acceptance. Return to the vacancy, resolve the issue, prepare a current
package and refresh the rehearsal. The server's clock enforces approval expiry.

The sandbox accepts at most one successful rehearsal per application. This deliberately
tests duplicate prevention; repeated rehearsal campaigns and real submission retries
are outside P6. A simulated success does not authorise future employer delivery.

## API and persistence

All routes use the existing authenticated session, ownership checks and CSRF boundary.

| Method and route | Purpose |
|---|---|
| `GET /api/v1/applications/{id}/submission` | Read the saved workflow, or `null` before preparation |
| `POST /api/v1/applications/{id}/submission` | Prepare from `package_id` and `package_version` |
| `POST /api/v1/submissions/{id}/authorise` | Confirm `expected_version`, `payload_hash` and `submission_confirmed: true` |
| `POST /api/v1/submissions/{id}/execute` | Execute an approved `expected_version` |
| `POST /api/v1/submissions/{id}/cancel` | Revoke an unused authorisation at `expected_version` |
| `POST /api/v1/submissions/{id}/reconcile` | Check the existing attempt at `expected_version`, without delivery |

The channel and recipient cannot be supplied by an advert, AI output or API caller.
Authorisation uses scope `submission:sandbox`. PostgreSQL unique indexes allow one
workflow and one receiver receipt per owner/application. An attempt UUID is created in
the committed dispatch checkpoint. Replaying execution while dispatch is pending returns
the saved state, without calling the receiver again.

Workflow revisions are preserved in append-only snapshots. State changes and audit events
commit together. Candidate export includes workflows, receipts, snapshots and audit
events; normal administrative erasure includes these records. Exports contain personal
content and belong outside Git. No new logging of document content is introduced.

## Verification

Run the complete API suite against a separate test database and the existing frontend
and browser commands in the [development guide](../local-development.md). Focused API
checks are:

```powershell
uv run --project apps/api --env-file .env pytest apps/api/tests/test_submissions.py apps/api/tests/test_submission_recovery.py
```

Set `JOBHUNTER_TEST_DB_NAME` to an isolated name beginning with `jobhunter_test` first.
Without it, integration tests skip and do not count as validation. Browser tests use
their own synthetic database and include cancellation, page reload and lost-response
recovery at desktop and mobile sizes. No live submission or AWS credentials are needed.

See [ADR-006](../adr/0006-controlled-submission.md) for the channel boundary and rationale.
