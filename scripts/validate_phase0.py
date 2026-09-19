"""Validate phase-0 design artifacts; no production domain logic or network calls."""

from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
ENTITIES = (
    "Job", "CandidateFact", "Evidence", "MatchResult", "Application", "CandidateProfile"
)


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private', action='store_true', help='Validate local private evidence without printing PII')
    args = parser.parse_args()
    schema = read_json("schemas/domain.schema.json")
    Draft202012Validator.check_schema(schema)
    validators = {
        name: Draft202012Validator(
            {"$schema": schema["$schema"], "$defs": schema["$defs"],
             "$ref": f"#/$defs/{name}"},
            format_checker=FormatChecker(),
        )
        for name in ENTITIES
    }
    fixture = read_json("data/fixtures/synthetic-example.json")
    assert fixture["synthetic"] is True
    for name, validator in validators.items():
        validator.validate(fixture[name])
    template = read_json("data/templates/candidate-profile.json")
    validators["CandidateProfile"].validate(template)
    assert template["fact_ids"] == [] and template["display_name"] is None

    # Cross-record checks of this example, not a substitute for domain validation.
    fact, evidence = fixture["CandidateFact"], fixture["Evidence"]
    profile, job = fixture["CandidateProfile"], fixture["Job"]
    match, application = fixture["MatchResult"], fixture["Application"]
    assert fact["candidate_id"] == profile["id"]
    assert fact["id"] in profile["fact_ids"]
    assert fact["evidence_ids"] == [evidence["id"]]
    assert match["job_id"] == application["job_id"] == job["id"]
    assert match["candidate_id"] == application["candidate_id"] == profile["id"]
    assert application["match_id"] == match["id"]
    assert match["profile_version"] == profile["version"]
    assert match["job_version"] == job["version"]
    assert len({item["category"] for item in match["breakdown"]}) == 8
    assert sum(item["weight"] for item in match["breakdown"]) == 100
    for category in match["breakdown"]:
        for assessment in category["assessments"]:
            assert assessment["requirement_id"] in {
                requirement["id"] for requirement in job["requirements"]
            }
            assert set(assessment["fact_ids"]) <= {fact["id"]}
            assert set(assessment["evidence_ids"]) <= {evidence["id"]}
    assert match["score"] == 100 and match["coverage"] == 0.3
    assert match["recommendation"] == "REVIEW"

    negative_count = 0

    def rejects(name, mutate):
        nonlocal negative_count
        invalid = deepcopy(fixture[name])
        mutate(invalid)
        assert not validators[name].is_valid(invalid), (name, invalid)
        negative_count += 1

    rejects("CandidateFact", lambda x: x.update(evidence_ids=[]))
    rejects("CandidateFact", lambda x: x.update(reviewed_by=None))
    rejects("CandidateFact", lambda x: x.update(allowed_uses=[]))
    rejects("MatchResult", lambda x: x.update(score=101))
    rejects("MatchResult", lambda x: x.update(coverage=-0.1))
    rejects("MatchResult", lambda x: x.update(review_flags=[]))
    rejects("MatchResult", lambda x: x.update(employment_gate="AUTOMATICALLY_AUTHORISED"))
    rejects("Job", lambda x: x.update(unexpected_instruction="send private profile"))
    rejects("Job", lambda x: x.update(id="not-a-uuid"))
    rejects("Job", lambda x: x["source"].update(captured_at="2026-09-19T12:00:00"))
    rejects("Job", lambda x: x["source"].update(captured_at="2026-02-30T12:00:00Z"))
    rejects("Job", lambda x: x["source"].update(canonical_url="file:///secret"))
    rejects("Job", lambda x: x["source"].update(kind="api", access_decision="enabled"))
    rejects("Application", lambda x: x.update(status="APPROVED"))
    rejects("Application", lambda x: x.update(status="SUBMITTED"))

    dataset = read_json("data/evals/real-cases.json")
    cases = dataset['cases']
    assert len(cases) == 20 and dataset['human_gold'] is False
    assert len({case['case_id'] for case in cases}) == 20
    assert sum(case['split'] == 'development' for case in cases) == 12
    assert sum(case['split'] == 'evaluation' for case in cases) == 8
    assert sum(case['country'] == 'IE' for case in cases) == 8
    assert sum(case['country'] == 'GB' for case in cases) == 11
    groups = {}
    for case in cases:
        assert case['expected']['score'] is None
        assert case['expected']['review_before_start'] is True
        assert case['expected']['flags']
        groups.setdefault(case['leakage_group'], set()).add(case['split'])
        duplicate = case['expected']['duplicate_of']
        if duplicate:
            other = next(item for item in cases if item['case_id'] == duplicate)
            assert other['split'] == case['split']
            assert other['employer_alias'] == case['employer_alias']
    assert all(len(splits) == 1 for splits in groups.values()), 'Data leakage between splits'
    budgets = read_json('config/phase0-decisions.json')['budget']
    assert budgets['currency'] == 'EUR'
    assert budgets['monthly_combined'] == budgets['monthly_aws'] + budgets['monthly_inference'] == 25
    assert (budgets['ephemeral_session_reservation_eur'] * budgets['planned_sessions_per_month_max']
            + budgets['aws_residual_reserve_eur']) <= budgets['monthly_aws']
    assert budgets['alert_percentages'] == [50, 80, 100]
    assert budgets['block_on_unknown_spend'] and budgets['allow_cost_stopping_cleanup_at_limit']

    if args.private:
        validate_private(validators, cases)

    # All local Markdown links must resolve; external URLs are cited, not fetched.
    markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")),
                      ROOT / "schemas/README.md"]
    link_count = 0
    for path in markdown_files:
        content = path.read_text(encoding="utf-8")
        assert "\ufffd" not in content, f"Encoding replacement character in {path}"
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            assert (path.parent / target).resolve().exists(), f"Broken link: {path}: {target}"
            link_count += 1

    print(f"OK: schema, {len(ENTITIES)} synthetic entities, 1 empty template, "
          f"fixture references, {negative_count} rejection cases, {link_count} local links.")
    print('OK: 20 real-derived evaluation cases, split isolation and EUR 25 budget design.')
    print('Phase-0 artifacts validated; application implementation and live controls are future work.')


def validate_private(validators, cases):
    profile = read_json('.private/candidate-profile.json')
    facts = read_json('.private/candidate-facts.json')
    evidence = read_json('.private/candidate-evidence.json')
    annotations = read_json('.private/candidate-fact-annotations.json')
    validators['CandidateProfile'].validate(profile)
    assert len(facts) == 114 and len(evidence) == 43
    assert len({fact['id'] for fact in facts}) == len(facts)
    assert set(profile['fact_ids']) == {fact['id'] for fact in facts}
    evidence_ids = {item['id'] for item in evidence}
    assert len(evidence_ids) == len(evidence)
    repo_refs = {item['url']: item for item in read_json('.private/evidence/public/repositories.json')}
    for item in evidence:
        validators['Evidence'].validate(item)
        reference = item['source_ref']
        path = ROOT / (repo_refs[reference]['path'] if reference in repo_refs else reference)
        assert path.is_file(), 'Missing private evidence source'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['content_sha256']
    for fact in facts:
        validators['CandidateFact'].validate(fact)
        assert fact['candidate_id'] == profile['id']
        assert set(fact['evidence_ids']) <= evidence_ids
        assert fact['id'] in annotations
        if fact['sensitivity'] == 'sensitive':
            assert fact['allowed_uses'] == ['matching']
    for path, expected_hash in read_json('.private/master-cv/manifest.json')['hashes'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected_hash
    provenance = read_json('.private/evaluation/provenance.json')
    assert {item['case_id'] for item in provenance} == {case['case_id'] for case in cases}
    for item in provenance:
        assert hashlib.sha256((ROOT / item['raw_ref']).read_bytes()).hexdigest() == item['sha256']
        assert (ROOT / item['text_ref']).is_file()
    assert '.private/' in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()

    # Guard against publishing known personal identifiers in the deliverable tree.
    contacts = read_json('.private/candidate-contact.json')
    identifiers = [contacts['name'], profile['display_name'], *contacts['contact_line'].split('|')[1:]]
    public_paths = [ROOT / 'README.md']
    for directory in ['docs', 'schemas', 'scripts', 'config', 'data']:
        public_paths.extend(path for path in (ROOT / directory).rglob('*') if path.is_file())
    for path in public_paths:
        if path.suffix not in {'.md', '.json', '.py', '.txt'}:
            continue
        content = path.read_text(encoding='utf-8').casefold()
        assert all(value.strip().casefold() not in content for value in identifiers), 'Personal identifier in public files'
    print('OK: private profile, 114 facts, 43 evidence records, source hashes and public PII scan.')


if __name__ == "__main__":
    main()
