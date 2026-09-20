# Project documentation conventions

Write all new and updated project documentation in British English (en-GB). This applies to
README files, guides, architecture decision records, specifications, reports, diagram labels,
wireframe text, explanatory comments and docstrings. Use British spellings such as
authorisation, behaviour, catalogue, colour, licence (noun), normalise and prioritise.

Before completing a task, review all documentation created or affected by the work and run
`python scripts/check_documentation.py`. Check meaning, links, commands, figures and consistent
British English; the automated check supports, but does not replace, editorial review.

Preserve exact code identifiers, environment variables, API routes, file paths, product names,
commands and version numbers. Preserve original supplied documents, captured evidence,
user quotations and raw model/evaluation outputs in their original language. Translate authored
explanations around them, and label any translation of evidence separately from the original.
Do not rewrite frozen datasets or stored responses merely to change their language.

Documentation language is independent of the application's interface language and the language
used to communicate with the user. Keep private documentation private and never include secrets
or personal source material in versioned documentation.
