import pytest
from conftest import claim, draft, step
from pydantic import ValidationError

from oauth_guides_api.builder import GuideBuilder, IncompleteGuide

HEADER = {"app_name": "Example", "website": "https://example.com", "developer_portal_url": None, "summary": ""}


def _record_all(builder: GuideBuilder, d) -> None:
    dumped = d.model_dump()
    builder.record("record_facts", {"facts": dumped["facts"], "stages": dumped["stages"]})
    builder.record("record_steps", {"steps": dumped["steps"]})
    builder.record("record_findings", {k: dumped[k] for k in ("requirements", "nuances", "blockers", "open_questions")})
    builder.record("record_artifacts", {"artifacts": dumped["artifacts"]})
    builder.record("record_composio", dumped["composio"])


def test_sections_assemble_into_the_same_guide():
    original = draft(steps=[step(claims=[claim("tested", ["s1"])])], requirements=[claim()])
    builder = GuideBuilder()
    _record_all(builder, original)
    assert builder.finish(HEADER) == original


def test_finish_names_every_missing_section():
    builder = GuideBuilder()
    builder.record("record_steps", {"steps": []})
    with pytest.raises(IncompleteGuide, match="record_facts, record_findings, record_artifacts, record_composio"):
        builder.finish(HEADER)


def test_invalid_section_is_rejected_and_resending_replaces_it():
    builder = GuideBuilder()
    with pytest.raises(ValidationError):
        builder.record("record_composio", {"managed_app_available": True})
    original = draft()
    _record_all(builder, original)
    builder.record("record_steps", {"steps": [step().model_dump()]})
    assert len(builder.finish(HEADER).steps) == 1


def test_missing_or_duplicate_facts_are_rejected_when_recorded():
    builder = GuideBuilder()
    stages = draft().model_dump()["stages"]
    facts = draft().model_dump()["facts"]
    with pytest.raises(ValidationError, match="facts must cover each"):
        builder.record("record_facts", {"facts": [], "stages": stages})
    with pytest.raises(ValidationError, match="facts must cover each"):
        builder.record("record_facts", {"facts": [*facts, facts[0]], "stages": stages})
    with pytest.raises(ValidationError, match="stages must list each audience"):
        builder.record("record_facts", {"facts": facts, "stages": [*stages, stages[0]]})
