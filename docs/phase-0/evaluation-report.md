# Initial dataset and review

Phase 1 update: [baseline run on the 20 cases and disagreements](../phase-1/evaluation-results.md). The text below records the original phase 0 preparation; it has not been retroactively converted into human gold-standard labels.

Twenty real adverts were read through GET requests to Greenhouse's public Job Board API during this phase. The versionable copy contains short paraphrases and employer aliases; originals, URLs, external IDs, timestamps and SHA-256 hashes remain in the private manifest `.private/evaluation/provenance.json`. No candidate data was collected and no forms were submitted.

The [dataset](../../data/evals/real-cases.json) contains 12 development cases and 8 evaluation cases. Labels were drafted by the assistant after documentary review: **they are neither a human-validated gold set nor algorithm execution results**. This distinction allows data preparation to finish in phase 0 and measurement/calibration to take place in phase 1.

## Observed coverage

| Cases | Behaviour to preserve |
|---|---|
| REAL-01/02 | Graduate role with an ambiguous experience limit; request interpretation rather than converting another career's experience into SWE years |
| REAL-03/04 | Internship requires ongoing studies; completed education does not prove current enrolment |
| REAL-05/06/07 | Commercial experience explicitly required; portfolio work does not become commercial employment |
| REAL-08/09/20 | Staff/Senior level excluded even with matching technologies |
| REAL-10 | Junior role accepts personal projects; absent sponsorship information does not block |
| REAL-11/13 | Same role on two boards; cross-source duplicate with different boilerplate |
| REAL-12 | Software engineer title and data engineer body; mandatory review and possible duplicate |
| REAL-14 | Graduation window, future start date and technology without evidence |
| REAL-15 | Multiple-level role and specific clearance rules; do not exclude on an isolated word |
| REAL-16 | Required B2B support is not automatically substantiated by internal support |
| REAL-17 | Conditional sponsorship and conflicting dates in the advert |
| REAL-18 | Mandatory MSc; do not equate a postgraduate diploma with a master's degree |
| REAL-19 | Negative control outside IE/UK, senior level and no sponsorship |

There are 8 adverts in Ireland, 11 in the United Kingdom and 1 outside the target markets as a negative control. Ten records come from the same employer; the sample is purposive and small, not representative of the market. It is not a recommended application shortlist.

## Deduplication and splits

Similar descriptions, duplicates and conflicts remain in the same split. Grouping includes REAL-10/11/12/13 and the graduate and internship pairs in different cities. There is one confirmed duplicate role across boards; the initial aim of collecting two confirmed pairs was not forced. The second pair found has conflicting content and serves as a review test, not an automatic merge.

A URL found in search returned 404 from the official API and was replaced with an accessible advert. Search results do not prove that a vacancy remains open. Before a real application, reread the deadline, content and availability.

## Publication and validation

Do not publish full adverts or personal contact details present in boilerplate. Public texts are limited analytical paraphrases. Pseudonymisation reduces direct identifiers, but titles and characteristics may still allow re-identification; do not claim irreversible anonymisation.

Validate counts, IDs, splits, groups without leakage, flags, absence of fabricated scores and local snapshot traceability. Human agreement review and accuracy/time baselines belong to the functional pilot, which has not yet run.
