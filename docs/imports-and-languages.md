# CV drafts, vacancy links and interface languages

## Import a CV

On the profile screen, choose a PDF, Word `.docx` or Markdown `.md`, confirm sending its extracted
text to OpenAI and select **Extract CV with AI**. The original file is not sent to
the provider. The draft shows the proposed name, facts, exact source excerpts and
warnings. Existing search preferences are retained; the model does not invent them.

The `cv-extraction-2.0` contract supplies numbered source lines. The model selects
an inclusive line range for each claim; the server copies the original contiguous
passage, including internal whitespace and intervening lines. It rejects invalid
ranges, blank or oversized passages, unsupported names and empty fact lists.
This avoids rejecting a valid PDF merely because the model reflowed a quotation.
The source reference establishes where a suggestion came from; it does not prove
that the model's interpretation is correct. Every claim still requires human review.

Add, edit or remove claims and check the original extracted text. A source excerpt
must remain a literal passage; leave it blank for a new candidate declaration.
Save the draft to resume later, or confirm its accuracy and permitted uses before
applying it. Applying updates the profile and creates reviewed facts and evidence
in one transaction. Existing facts are retained and identical claims in the same
category are skipped. Repeated application cannot create duplicates. Publishing a
profile version remains a separate action.

Limits: 4 MiB, 20 PDF pages, 50,000 extracted characters and 80 draft facts. Older
`.doc` files need conversion to `.docx`; scanned PDFs need OCR before upload.
Encrypted, malformed or oversized files are rejected. Text parsing runs in a
disposable process with a 25-second timeout, without inherited API/database secrets.
Linux also imposes memory and CPU limits. DOCX extraction reads bounded XML without
extracting archives to disk, resolving external entities or running macros. The
process is not a separate container or a complete security sandbox.
Markdown must use UTF-8 (an optional BOM is accepted). It is read as plain source
text: embedded HTML, scripts, images and links are never rendered, executed or fetched.

When extraction fails, the profile stays unchanged and **Retry CV extraction** makes
an explicit new attempt. Requests use idempotency keys, successful extractions remain
cached and the existing budget and retry limits still apply. No automatic paid retry
is performed. You can also upload an alternative supported format. Draft text survives
switching between profile sections; comma-separated preferences retain spaces while typing.

Private drafts retain extracted text, a source-file hash, excerpts and the AI run
reference locally. They are included in authenticated export and administrative
erasure. The original upload bytes are not retained. Extraction uses the existing
budget ledger and cache, with `JOBHUNTER_AI_CV_MODEL`, `JOBHUNTER_AI_CV_EFFORT` and
`JOBHUNTER_AI_CV_PROMPT_SUFFIX`. Docker defaults to GPT-4.1 mini; direct API settings
fall back to `JOBHUNTER_AI_MODEL` when no CV model is specified.
The CV output allowance is 12,000 tokens, reserved before calling the provider.
Review establishes a candidate declaration, not independent verification.

## Import a vacancy link

In **Import vacancy**, choose **From a link**, enter a public HTTPS vacancy URL and
confirm reading the page and sending its text to OpenAI. The application extracts
the readable text, prefers a single structured `JobPosting` when available, imports
the source and creates a draft with the existing AI parser. Check every field and
requirement before confirming the job review. Missing information stays unknown.

The reader checks public IPv4/IPv6 destinations, pins the validated address for the
TLS connection and revalidates redirects. It uses no browser, credentials, proxy
environment variables or page scripts. It checks `robots.txt` and rejects restricted
pages, private addresses, unsupported content and multiple structured vacancies.
It does not bypass login or CAPTCHA. Automated LinkedIn access remains disabled.
Reads have bounded socket timeouts, a shared time budget, a 2 MiB response limit,
limited redirects and a 50,000-character extracted-text limit.

Some sites require JavaScript or deny automated access. Use **Paste text** in those
cases. If reading succeeds but AI extraction fails, the imported source remains
available for manual review; the interface provides a link to it. Reimporting an
existing reviewed job does not overwrite its reviewed fields.

## Job review

The review confirmation checkbox is required. A visible explanation and validation
message identify it when submission is attempted without confirmation. The archive
help icon explains that archiving hides an opportunity from the active Inbox while
retaining its history, and how to restore it through the archived filter.

**Save vacancy review** advances to **2. Assess requirements** only after a successful
save. The next step receives the saved job version immediately and keyboard focus
moves to the stage content. Failed saves keep the current form and entered values.
If the profile needs publishing or the vacancy has no requirements, the next step
explains what is missing and offers a route back to the appropriate screen.
Unsaved search-profile edits must be saved before publishing its version.
Switching between vacancy link and text import preserves both inputs.
Transient connection failures on read-only API requests are retried once. Write
requests, including paid extraction, are never automatically repeated. Persistent
connection failures show a translated recovery message rather than a browser error.

## Interface language

Use **Language** on the login screen or session bar to select **English (UK)** or
**Português**. British English is the default. The browser remembers the choice in
local storage, updates the page language for assistive technology and changes labels
without remounting forms or discarding unsaved input. Dates follow the selected locale.

The source labels are British English; Portuguese translations are maintained in
`apps/web/src/locales/pt.json`. New interface messages must use the translation
helpers, keep stable data keys and preserve placeholder numbers. Catalogue tests
check static message coverage and placeholder consistency.

Original adverts, evidence quotations, candidate declarations and previously stored
AI responses retain their original language. New AI explanations use British English;
the interface selector does not translate factual source material or regenerate AI
responses. Downloaded application document templates remain British English.
Project documentation remains British English regardless of the interface choice.

## Validation and limits

The added tests cover genuine PDF/DOCX parsing, malformed and macro-bearing files,
literal source quotations, consent, draft editing and application, idempotency,
profile conflicts, private and mixed DNS destinations, pinned TLS connections,
redirects, access rules, structured vacancy data and recovery from AI failure.
Browser tests exercise draft editing and resumption, language switching with unsaved
input, persistent language choice, link extraction, review confirmation and archive
help at desktop and mobile sizes. Browser AI responses and remote pages are synthetic
fixtures in an isolated test database.

On 20 September 2026, separate live GPT-4.1 mini checks extracted two quoted facts
from a synthetic Word CV and confirmed that repeating the request used the cache.
A real public vacancy page was read through the production URL reader; AI extracted
its title and six requirements, with source quotations passing local validation.
These checks did not change candidate facts or add a vacancy to the personal Inbox.
Their paid calls used the existing budget ledger. They are integration smoke tests,
not a measurement of extraction accuracy across CV layouts or vacancy websites.

Local validation passed 113 API tests, 18 frontend tests and ten browser tests
(five workflows at desktop and mobile sizes), plus type, lint, formatting, build,
historical evaluation and documentation checks. Browser tests used Microsoft Edge
locally; CI retains its configured Chromium installation.

A follow-up regression check used the privately supplied two-page PDF. The original
contract reproduced a validation failure: copied quotations changed layout whitespace
and one quotation joined non-adjacent passages. The replacement contract extracted
35 draft facts with exact source passages; a repeat used the cache. Candidate records
were not changed. The source CV and detailed results remain private. Public regression
fixtures cover wrapped source lines, invalid ranges, UTF-8 Markdown, explicit retry
after validation failure, draft resumption, multi-word preferences, failed job saves
and automatic progression. Desktop and mobile browser checks also cover the existing
matching, evidence, application package, tracker and export workflows.

The wording changes have new prompt versions: parser `job-parser-1.4-en-GB`, matching
`evidence-matching-1.3-en-GB`, strategy `application-strategy-1.2-en-GB` and public
research `public-research-1.1-en-GB`. Historical benchmark files and raw responses
remain unchanged. Offline benchmark checks retain their recorded prompt versions
and normalise only the exact translated guardrail label when comparing historical
matching output. Historical scores do not certify these newer prompt versions.

## Sources

The implementation uses the existing adapter's strict schema and local validation;
see [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
PDF text extraction has limitations, particularly for scanned documents; see
[pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
URL controls follow the DNS and destination validation principles in the
[OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
