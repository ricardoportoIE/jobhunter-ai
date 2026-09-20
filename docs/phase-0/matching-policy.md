# Matching policy v0.2

Final phase 0 definition, based on supplied preferences and the review of real vacancies. The profile and exact personal constraints remain in `.private/`.

## Search priorities

Graduate/junior backend roles in Python or Java first; software/full-stack next; automation and applied AI afterwards. Cloud/platform roles are alternatives when they include programming or automation. Data analyst/data engineer roles are not primary targets. Search Ireland before the United Kingdom, favouring hybrid Dublin, on-site Dublin and remote work within Ireland. Other cities, salaries and relocation are assessed case by case: no minimum salary or maximum radius is confirmed.

Full-time work is the objective. Part-time work may be a bridge without replacing that priority. Senior, Lead, Principal, Staff, Manager, Head and Architect are excluded when they describe the role's level. Do not apply this filter to incidental mentions such as ‘collaborate with senior engineers’ or to roles explicitly open to multiple levels.

## Separate searching from starting work

A candidate may pursue an offer requiring new authorisation before starting. Absence of sponsorship information in an advert means `unknown`, not ‘unavailable’. The need for a future authorisation change is not, by itself, a search blocker and does not automatically reduce the technical score.

The result includes `employment_gate`: `READY_WITHIN_CONFIRMED_LIMITS`, `REVIEW_BEFORE_START` or `BLOCKED`, alongside the recommendation and flags. A technically suitable role may receive `APPLY_AFTER_REVIEW` and `REVIEW_BEFORE_START` simultaneously. This never authorises starting work or answering ‘unrestricted authorisation’ on forms.

Block or strongly deprioritise when a mandatory condition is explicitly incompatible: no sponsorship when employer support is necessary, non-negotiable permanent unrestricted authorisation, an advanced level, unsupported mandatory commercial experience, or a demonstrably unfeasible location. A legal inference that ‘no route is possible’ requires sufficient facts and human review; the LLM does not decide alone.

Immigration rules are time-dependent and specific. Official Irish guidance distinguishes hours limits by period; retain the conservative declared limit until review, without automatically updating rights according to the calendar. The British Skilled Worker route requires an offer and an approved employer, with its own conditions. References: [ISD student guidance](https://www.irishimmigration.ie/coming-to-study-in-ireland/frequently-asked-questions-for-students/) and [GOV.UK Skilled Worker](https://www.gov.uk/skilled-worker-visa/your-job). These sources inform flags; they do not confirm individual eligibility.

## Factual rules learnt during analysis

- Experience in another career and additional support duties do not equal years of employment as a software engineer.
- A postgraduate qualification comparable to a Post-Graduate Diploma must not be presented as an MSc.
- Certifications, diplomas, awards and test metrics retain their evidence type: candidate declaration, public documentation or independent verification.
- Projects under development do not count as completed deliveries; conceptual knowledge of RAG/agents does not demonstrate production experience.
- Two adverts with identical text in different cities are not automatically the same opportunity.
- A conflict between a job title and body requires review; do not silently resolve it by choosing the title.

## Acceptance criteria

A junior full-time role with good technical suitability and unknown sponsorship remains visible/recommendable with review. Explicit refusal of sponsorship retains its reason. Missing salary remains null. Mandatory commercial experience is not fulfilled by adding years in another profession. Profile or advert changes invalidate old analyses. See the [real-world dataset](../../data/evals/real-cases.json).
