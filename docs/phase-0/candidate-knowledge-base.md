# Master CV and Candidate Knowledge Base

## Separating the template from real data

`data/templates/candidate-profile.json` is a validatable blank form. Copy it to `.private/candidate-profile.json` and fill it in only with reviewed information. `.gitignore` reduces accidental publication; it neither encrypts files nor replaces access control. Use protected local storage and inspect the diff before every commit.

The master CV remains private in `.private/master-cv/`. Private evidence is stored in `.private/evidence/`. The supplied DOCX and PDF were read and compared: 60 paragraphs match after text normalisation; the two-page PDF was visually inspected. Originals were preserved with SHA-256 hashes. The old `data/cv/` path mentioned in the material does not exist and was not created for personal data.

Consolidated base: 114 facts, 43 evidence records and four repository references pinned to commits. The user confirmed in this conversation that the CV's facts and dates are current. `verified` represents that approved declaration, supplemented by public documentation where available; no project tests were rerun. Qualifications and awards retain declarative provenance pending any documentary verification, without presenting a postgraduate diploma as a master's degree.

Private files: `candidate-profile.json`, `candidate-facts.json`, `candidate-evidence.json`, `candidate-fact-annotations.json`, `candidate-constraints.json` and `candidate-contact.json`. Contact details and sensitive constraints remain separate. Unnecessary personal data remains null. A project under development is not a completed delivery fact.

## Consolidation process

1. Record the original CV's version, date and hash, retaining an unchanged copy.
2. Extract atomic facts: one experience, skill, certification or achievement per record.
3. Associate evidence and its exact location: page, section, file/commit or approved candidate declaration.
4. Keep extracted facts `unverified` until review. A CV is a declarative source, not independent confirmation.
5. Define validity, permitted uses and sensitivity classification.
6. Review contradictions, dates and metrics with the candidate; never silently choose one version.
7. Publish an immutable profile snapshot with fact revision IDs for matching and generation.

## Validity rules

`verified` means that the candidate has approved the claim and its sources for use. It does not mean independent external verification. `unverified`, `expired` or `revoked` facts cannot feed factual generation. Validity is checked on every execution. Revocation invalidates packages that have not yet been submitted and requires a new review.

A revision creates a new fact ID and increments the profile version. Old records used in evaluations remain referenceable, subject to the personal data erasure policy. Audit logs retain minimal identifiers and hashes, not sensitive text.

Immigration, work authorisation, salary and availability constraints must be held in separate private records with jurisdiction, validity and human review. The application does not infer legal rights from nationality or location.

## Input fields

| Group | Content | If missing |
|---|---|---|
| Preferences | Roles, markets, locations, working arrangements | Request configuration; do not invent filters |
| Experience | Employer, role, dates, supported responsibilities | Do not generate claims |
| Projects | Repository, personal role, technologies, deliverables | Do not assume authorship or proficiency |
| Education | Course, institution, dates and status | Unknown |
| Constraints | Hours, authorisation, sponsorship, availability, salary | Mark as requiring review |
| Evidence | Provenance, hash, location and review date | Fact remains unverified |

## Proposed retention

Active private documents: while needed for the job search. Raw job content and attachments: 90 days by default. Rejected packages: 90 days. Closed application history: review necessity after 12 months. Redacted operational logs: 30 days. Backups: a 30-day window, with deletions reapplied after restoration. These are initial product choices to confirm, not prescribed legal periods.

An erasure request must remove files, embeddings, fact content, caches and provider copies where applicable. Retain only justified minimal pseudonymised audit records; do not use soft deletion as a substitute for erasure.
