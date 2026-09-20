# P3 — Prepare and approve an application

Open a reviewed job and choose the fourth tab, the application package. The profile must
be published with a name; the job must have a role and company.

1. Select reviewed facts with current evidence and permission for the intended documents:
   `cv`, `cover_letter` and/or `application_form`. The `matching` permission alone does not
   authorise documents. Facts and evidence marked as sensitive are excluded from automatic selection.
2. Enter up to four contact lines and, optionally, form questions, one per line.
   Contact details remain in the local package.
3. Prepare the strategy. With AI, confirm sending the selected facts, evidence content, job
   requirements and questions to OpenAI. The contact field, profile name and source paths are
   not sent; evidence text may contain personal data, so check your selection. Manual mode is also available.
4. Review relevance, gaps and interview points. Adjust the selection and order of CV and
   letter facts; confirm review and approve the strategy.
5. Generate the package. Check the text and each claim's provenance. Answers without evidence
   must be completed and declared true by you. Salary, immigration, availability and other
   sensitive questions require specific review.
6. Save changes as a new version and consult history and differences. Check the English and
   presentation; approve the version to enable downloads.

Available files: `cv.docx`, `cv.pdf`, `cover-letter.docx`, `cover-letter.pdf`,
`answers.json`, `package.json` and a ZIP containing them all and a SHA-256 manifest.
Choose appropriate files before sharing: the JSON files and ZIP include answers and provenance
references that the employer may not need.

## How content remains verifiable

AI proposes ID selection and explains relevance/gaps. A deterministic validator checks IDs,
permissions, requirement coverage and questions. Generation copies approved fact claims
literally, including names, dates and roles. Subsequent validation reconstructs content and
compares it for equality, checks pending answers and records warnings. No second model issues
a truthfulness judgement on free text.

Document templates use British English. Facts are not translated or rewritten automatically:
to change a claim, correct and review the fact in the canonical base, publish the profile when
needed and generate another strategy. The letter uses fixed opening and closing text with
selected facts; it does not invent company research or personal motivation. The CV groups
facts by category, preserving the selected order within each group.

Approval records the user, date, version and content hash. Changing the package revokes
approval; changing or expiring a source blocks new approvals and downloads for that package.
Previous strategies and versions remain available for consultation. Approval neither submits
an application nor automatically changes the tracker.

## Privacy, costs and operations

Documents are rendered in memory by the local backend using `python-docx` and ReportLab.
The runtime does not depend on Word, LibreOffice or cloud converters. Downloaded JSON omits
the full snapshot and private evidence paths. Snapshots, answers and history are included in
local data export and erasure; already downloaded files remain under your control.

Calls use P2's model, cache, budget reservations and ledger, visible in the AI activity screen.
The €10/month AI and €25 combined ceilings remain, as described in [P2 operations and privacy](../phase-2/operations.md).
Manual mode and local rendering do not consume API usage. The default configuration uses GPT-4.1 mini.

HTTP contracts are in [local OpenAPI](http://127.0.0.1:5173/api/docs).
P3 uses existing `records` and `snapshots`, without a new migration. Routes cover per-job
strategy, strategy approval, generation, package update/review, history/diff and authenticated
download with an expected version.

Limitations: sensitive-question classification is heuristic; all answers remain subject to
human review. Manual answers are candidate declarations without independent verification.
The layout is single-column and ATS-oriented, but has not been certified by external ATS services.
Long content may produce several pages; check downloaded files before submitting.
