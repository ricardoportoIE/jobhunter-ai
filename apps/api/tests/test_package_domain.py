from datetime import UTC, datetime

import pytest

from jobhunter_api.package_domain import choose, sensitive
from jobhunter_api.scoring import eligible


def test_document_permission_is_not_matching_permission() -> None:
    evidence = {"e": {"reviewed_at": "now", "version": 1}}
    fact = {
        "status": "verified",
        "reviewed_at": "now",
        "reviewed_by": "owner",
        "evidence_ids": ["e"],
        "evidence_versions": {"e": 1},
        "allowed_uses": ["cv"],
    }
    assert eligible(fact, evidence, datetime.now(UTC), "cv")
    assert not eligible(fact, evidence, datetime.now(UTC))
    assert not eligible(fact, evidence, datetime.now(UTC), "cover_letter")
    with pytest.raises(ValueError):
        choose(["f"], {"f": fact}, "cover_letter")
    with pytest.raises(ValueError):
        choose(["f", "f"], {"f": fact}, "cv")
    evidence["e"]["version"] = 2
    assert not eligible(fact, evidence, datetime.now(UTC), "cv")


@pytest.mark.parametrize(
    "question",
    [
        "Expected salary?",
        "Direito de autorização de trabalho?",
        "When are you available?",
        "Criminal record?",
        "Your gender?",
    ],
)
def test_sensitive_questions_cannot_be_auto_approved(question: str) -> None:
    assert sensitive(question)
