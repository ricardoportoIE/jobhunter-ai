# A simpler frontend experience

The interface centres on three tasks: build a profile, explore saved opportunities and
track applications. The design uses a light canvas, restrained blue accents, consistent
spacing and labelled icons. It adapts to desktop and mobile screens without requiring
users to understand the application's internal data model.

## Start with the next useful action

P6 extends **Applications** with an optional local rehearsal. A final content review,
separate confirmation and expiring authorisation lead to a clearly labelled simulated
receipt. Recovery reads the saved workflow before offering another action; a lost
response never triggers automatic resubmission. The real tracker status is preserved.

The main navigation contains **Opportunities**, **My profile** and **Applications**.
**Import vacancy** remains a prominent action. Privacy, semantic search and AI activity
are available under **More tools**, with their existing routes preserved.

An incomplete profile receives a short introduction and a direct route to CV upload.
A reviewed profile receives a compact readiness message instead. The opportunities page
describes the list as saved vacancies: it does not imply that the application searches
the internet for jobs automatically.

On **My profile**, CV upload is the main action. **Edit details and preferences** reveals
the optional manual form, and **Manage facts and sources** reveals the detailed editors.
CV drafts show a readable list of claims; open an item to inspect or edit its source,
category and sensitivity. Newly added claims open for editing. The separate profile
form is hidden while a CV draft is being reviewed, avoiding two competing name and
preference forms. Switching sections or languages preserves draft input.

Applying a reviewed CV remains separate from **Confirm my profile**. Existing facts
are preserved. A confirmation publishes the current profile version; it does not
independently verify the truth of a candidate's declaration.

## Find and review a vacancy

The primary filters are title/company, location and working arrangement. Stage and
archive filters are available under **More filters**. **Clear filters** resets every
field and returns to the first page. Pagination appears only when needed, and an empty
filtered result offers recovery instead of suggesting the user has never added a job.

Filtering runs in PostgreSQL before pagination. Title/company and location are
case-insensitive literal substring searches; SQL wildcard characters are escaped and
all values are bound parameters. Working arrangement uses a validated enumeration.
Unknown locations or arrangements remain visible without the corresponding filter;
they do not satisfy a specified location or arrangement. Ownership and archive rules
continue to apply to both results and counts.

Link import remains the default. Pasted text is available as an alternative, with
optional source metadata behind a disclosure. Job review focuses on the essentials:
individual requirements, salary and eligibility details, original text, research and
duplicate tools can be expanded when needed. Explicit disqualifiers appear in each
requirement's summary. The required review confirmation and explanation stay visible.
Saving successfully advances to requirement assessment; a failed save preserves input.

## Reduce repetitive AI setup

Matching preselects up to 20 verified, non-sensitive facts with permission for matching
and currently valid dates. This is deterministic convenience selection in the profile's
existing order, not an AI relevance ranking. If more than 20 facts qualify, a visible
message asks the user to choose the relevant subset. The selected count is always
visible, and **Choose facts and review what is shared** exposes the complete selection.

Selecting facts does not call the provider. The user still authorises external
processing and explicitly requests suggestions. The first current AI response fills
the editable assessment draft and leaves confirmation unchecked. It does not calculate
a score, resolve a conflict, publish facts or approve an application. Later assessments
remain available for comparison and require an explicit action to populate the draft;
a second opinion never silently replaces the first with a more favourable conclusion.

Changing the selected facts clears consent and prevents applying the previous suggestion.
An AI retry is bound to the selection that authorised it; changing that selection removes
the old retry action. The user can start a new request with the revised disclosure.
Backend evidence checks, clarification gates, deterministic weights, budget limits and
version checks remain authoritative.

## Validation

Final local verification on 20 September 2026 passed **115 API tests, 24 frontend tests
and 12 browser tests** across desktop and mobile. Lint, formatting, strict type checks,
evaluation contracts, documentation checks, application builds and database recovery
also passed. Visual inspection covered the captured screens; axe checks passed after
correcting secondary text contrast. Two existing upstream Python deprecation warnings
remain visible.

Regression tests cover combined filters before pagination, unknown fields, literal
wildcards, invalid filters, eligibility boundaries, consent, selection changes, retry
scope and first-draft versus second-assessment behaviour.

Playwright exercises the new navigation and filters alongside the existing CV,
extraction, matching, document, tracker, privacy and recovery journeys. The guided
journey captures login, onboarding, profile, import and populated opportunities screens
on desktop and mobile. It also checks layout at 320 pixels with an alternative system
font, compares content width against the requested viewport and runs axe checks for
WCAG A/AA rules on the principal screens. These automated checks complement visual
inspection and keyboard tests; they are not a claim of complete accessibility certification.

Run the checks in [local development](local-development.md). Browser tests use synthetic
data and an isolated database. No new live model benchmark is needed for this interface
change: the inference adapter, prompts and model configuration are unchanged.

Each browser journey resets only the login throttle bucket in `jobhunter_test_e2e`.
This prevents unrelated synthetic logins in a larger suite from consuming one another's
allowance. The reset requires the test-only runner and its fixed database name; it is
not an application endpoint. Production login limits and their API tests are unchanged.
