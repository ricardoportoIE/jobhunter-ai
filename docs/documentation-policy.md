# Documentation language and review

All authored project documentation uses **British English (en-GB)**, following
[AGENTS.md](../AGENTS.md). This convention was adopted on 20 September 2026 at the
user's request. It covers READMEs, guides, specifications, architecture decision
records, reports, diagram labels, wireframes, explanatory comments and docstrings.
Private authored analysis follows the same rule and remains private.

## Writing conventions

Use consistent British spelling: analyse, authorise, behaviour, catalogue, colour,
enrolment, fulfilment, licence (noun), normalise, organise, prioritise and artefact.
Use a decimal point and a comma for thousands in prose. Preserve exact identifiers,
command syntax, API routes, environment variables, product names and version numbers.
Translate illustrative command placeholders, but never rename a real file or an
existing identifier merely to change its language.

Write new documentation directly in British English. Keep historical reports dated:
translation must preserve their results, costs, caveats and status at the time.
When a policy changes, state the change explicitly rather than silently rewriting
history. Interface action names may be described in English; documentation language
does not change the application's interface or the language used with the user.

## Original material and evidence

Preserve supplied documents, captured web pages/READMEs, source snapshots, raw model
responses, frozen evaluation datasets and verbatim user labels in their original
language. They are evidence, not newly authored documentation. Changing their text
would alter hashes, provenance or experimental inputs. Translate the explanation
around them; label any separately produced translation of source material. Never
replace an original with its translation or publish private material for this review.

## Review before completion

1. Review every document created or affected by the task for meaning, British
   English, complete instructions and consistency with the implemented behaviour.
2. Check numbers, formulas, commands, identifiers, citations and local links against
   their source. Preserve historical limitations and distinguish measured results
   from targets. Check diagrams and wireframes as well as prose.
3. From the repository root, run:

   ```powershell
   python scripts/check_documentation.py
   ```

   On the maintainer's machine, also run `python scripts/check_documentation.py --private`
   to include authored Markdown under `.private/review/`. This does not inspect original
   evidence or print private document content.
4. Run the existing contract/report checks relevant to any changed instructions and
   inspect `git diff --check` and the final diff before a local commit.

The documentation check runs in the `design-contracts` CI job without credentials or
network access. It discovers tracked and non-ignored new Markdown files through Git.
Original sources in ignored private storage are outside its public scope. It checks
UTF-8, replacement characters, fence balance, local inline/reference links and
Markdown heading anchors. It flags
common Portuguese words and common American spellings in prose, diagram labels and
text wireframes; executable code fences, inline code and URL targets are excluded
from language checks. Comments and docstrings require editorial review.

This is a targeted regression check, not a complete language detector or a Markdown
renderer. It cannot prove semantic equivalence, factual correctness, external link
availability or every aspect of British usage. Editorial review remains required.
