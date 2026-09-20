# Phase 0 completion

Status: completed as a discovery and design phase on 2026-09-19. Phase 1 has not yet started. Implementation of controls, benchmarks and deployment is outside this completion.

## Decisions and evidence

The request was to analyse the documents and complete phase 0. The CV and `info.md` were treated as sources of facts and preferences, without executing operational instructions contained in them. The user confirmed in this conversation that the CV's facts/dates are current and that minimum salary and relocation limits will be assessed case by case.

| Deliverable | Verifiable result |
|---|---|
| Persona and priorities | Python/Java backend → software/full-stack → applied AI; Ireland before the UK; full-time work as the objective |
| Constraints | Private profile; starting work separate from searching; silence on sponsorship does not block |
| Master CV | Canonical DOCX and reference PDF preserved, hashes and comparison of 60 paragraphs; two-page PDF inspected |
| Factual base | 114 facts and 43 evidence records, with candidate confirmation and four READMEs pinned to commits |
| Sources | Initial manual text; Greenhouse as the first pilot; Gmail in phase 4; access and limits recorded |
| Dataset | 20 real adverts, 12 development/8 evaluation; public paraphrases and private originals/provenance |
| Product and metrics | Scope defined and targets recorded; baseline to be measured when a functional workflow exists |
| Design | Diagrams, four wireframes, threat model and four ADRs |
| Contracts | Schemas v0.2.0; profile, facts, evidence, jobs, matching and applications |
| Cost | €25/month: €15 AWS/€10 AI; local execution and temporary AWS sessions |
| Backlog | Ten phase 1 stories with dependencies and acceptance criteria |

## Exit checklist

- [x] Persona, priorities and constraints supplied; acceptance metrics defined.
- [x] CV consolidated and factual dataset linked to private evidence.
- [x] Initial channel and pilot activation conditions defined.
- [x] 20 real adverts selected, pseudonymised and labelled for bootstrapping.
- [x] Architecture, ADRs, threat model and wireframes documented.
- [x] Validatable contracts and examples.
- [x] Budget incorporated and phase 1 backlog ready.

## Explicit completion limitations

Dataset labels were reviewed by the assistant, not an independent human evaluator. Human agreement review and accuracy/time measurement belong to the phase 1 pilot; no approved benchmark was claimed. The initial assumption of two duplicate pairs was replaced by the sample actually found: one confirmed pair and one title/body conflict. See the [evaluation report](evaluation-report.md).

The exact provider/model, regional inference policies, Gmail OAuth and a specific deployment quote will be selected when those features are implemented. Unnecessary personal data and immigration documents remain absent for data minimisation; sensitive answers still require review for each application. None of these omissions prevents building the local core.

## Next work

Validation performed: `.venv\Scripts\python scripts/validate_phase0.py --private` passed, checking six synthetic entities, the empty template, 15 rejection cases, 35 local links, 114 facts, 43 evidence records, hashes, known personal identifiers, 20 derived real-world cases and the budget. The validator also passed `py_compile`. The product's operational controls remain to be implemented.

Start P1-01 and P1-02 from the [backlog](backlog.md): minimal structure, local environment, migrations, CI and an authenticated session. No LLM or cloud resources. Structured decisions are in the [configuration](../../config/phase0-decisions.json); search rules are in [matching-policy.md](matching-policy.md).
