# CV drafts, vacancy links and interface languages

## Import a CV

On the profile screen, choose a PDF or Word `.docx`, confirm sending its extracted
text to OpenAI and select **Extract CV with AI**. The original file is not sent to
the provider. The draft shows the proposed name, facts, exact source excerpts and
warnings. Existing search preferences are retained; the model does not invent them.

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

Private drafts retain extracted text, a source-file hash, excerpts and the AI run
reference locally. They are included in authenticated export and administrative
erasure. The original upload bytes are not retained. Extraction uses the existing
budget ledger and cache, with `JOBHUNTER_AI_CV_MODEL`, `JOBHUNTER_AI_CV_EFFORT` and
`JOBHUNTER_AI_CV_PROMPT_SUFFIX`; the default model follows `JOBHUNTER_AI_MODEL`.
The CV output allowance is 12,000 tokens, reserved before calling the provider.
Review establishes a candidate declaration, not independent verification.

## Import a vacancy link

In **Import advert**, choose **From a link**, enter a public HTTPS vacancy URL and
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

## Sources

The implementation uses the existing adapter's strict schema and local validation;
see [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
PDF text extraction has limitations, particularly for scanned documents; see
[pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
URL controls follow the DNS and destination validation principles in the
[OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
