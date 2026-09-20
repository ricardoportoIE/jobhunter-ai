# Four screens for the first workflow

Low-fidelity wireframes, without an implemented application. Illustrative text and numbers; no real data. Workflow: Profile → Inbox/import → Details/analysis → Tracker. The overview will be an Inbox summary; document review gains its own screen in phase 3.

## 1. Profile and evidence

```text
+------------------------------------------------------------------------+
| JobHunter AI     Jobs | Profile | Applications                         |
| Profile — version 1                         [New revision]             |
| Roles: [to be completed]  Markets: [to be confirmed]                   |
| Private constraints: incomplete             [Review privately]         |
|                                                                        |
| Fact                  Status          Evidence           Actions       |
| Synthetic example     Unverified      [Add]              [Review]      |
|                                                                        |
| [Add fact]  [Add source]  [Publish reviewed version]                   |
| Only verified, current facts support applications.                     |
+------------------------------------------------------------------------+
```

The empty state requests facts and evidence without automatic approval. Evidence details show provenance, location, validity and uses. Sensitive fields are absent from listings and the profile summary.

## 2. Inbox and import

```text
+------------------------------------------------------------------------+
| Jobs                                        [Import job text]          |
| [Country] [Working arrangement] [Score] [Status] [Review required]     |
|                                                                        |
| Role / synthetic company          Score    Coverage    Status          |
| Junior Backend / Company A        68/100   50%         Review data     |
| Graduate / Company B              —        —           Review fields   |
|                                                                        |
| Import: [description text.........................................]    |
| Optional source/URL: [............................................]    |
| [Save and review fields]                                               |
+------------------------------------------------------------------------+
```

The URL is provenance; phase 1 does not visit it. Validation errors appear beside fields. Duplicate detection presents the existing record and an option to review its version, without silently creating another application.

## 3. Details and analysis

```text
+------------------------------------------------------------------------+
| Junior Backend / Company A           [Review requirements] [Analyse]   |
| Source and date | Job v1 | Profile v1 | Algorithm 0.2                  |
| Score 68/100 | Coverage 50% | REVIEW REQUIRED                          |
| Insufficient data: authorisation and working arrangement unconfirmed.  |
|                                                                        |
| Category         Weight     Attainment     Coverage                    |
| Skills           30%        80%            100%                        |
| Experience       20%        50%            100%                        |
| Other            50%        unknown        0%                          |
|                                                                        |
| Met [evidence] | Partial [evidence] | Gaps | Blockers                  |
| [View description] [Save to shortlist] [Archive]                       |
+------------------------------------------------------------------------+
```

The example follows ADR-003. Blockers have text and do not depend on colour. Display unknown separately from unmet. If the profile changes, mark the analysis as stale and request a new run.

The details also show ‘Starting work: review required’ and the associated flags. A positive recommendation can coexist with unknown sponsorship; do not hide the job or present permission to start as confirmed.

## 4. Tracker

```text
+------------------------------------------------------------------------+
| Applications        [Status] [Company] [Record manual submission]      |
| Shortlist          | Submitted        | Interviews      | Closed       |
| Company A          | Company B        |                 |              |
|                                                                        |
| Application details                                                    |
| Timeline: created → note → confirmed manual submission                 |
| Channel: [........]  Date: [........]  Supporting record: [........]   |
| [Confirm manual record]                                                |
+------------------------------------------------------------------------+
```

Recording a manual submission updates history and sends nothing externally. The future package screen will show the CV, letter, diff, evidence and sensitive fields; package approval and final submission confirmation will be separate actions.

## Shared interaction

Keyboard navigation, visible focus, explicit labels, adequate contrast, loading/empty/error messages and success confirmation. On small screens, cards/lists replace tables and Kanban. Do not enable actions requiring a valid snapshot when requirements are missing.
