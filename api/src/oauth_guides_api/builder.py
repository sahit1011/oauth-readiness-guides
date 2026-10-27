"""Assembles a GuideDraft from sections the agent records one tool call at a time.

One giant submit call made some models emit malformed JSON for a nested field (reproduced on a free
OpenRouter model: `composio` arrived as an unparseable string, 13 resubmissions in one run). Small
section calls keep each payload short, let the agent fix one section at a time, and give the live
view a milestone per section. Recording a section again replaces it.
"""

from pydantic import BaseModel, model_validator

from .schema import Artifact, Blocker, Claim, ComposioNote, Fact, GuideDraft, Stage, Step, check_facts_and_stages


class FactsSection(BaseModel):
    facts: list[Fact]
    stages: list[Stage]

    @model_validator(mode="after")
    def _facts_and_stages(self) -> "FactsSection":
        check_facts_and_stages(self.facts, self.stages)
        return self


class StepsSection(BaseModel):
    steps: list[Step]


class FindingsSection(BaseModel):
    requirements: list[Claim]
    nuances: list[Claim]
    blockers: list[Blocker]
    open_questions: list[str]


class ArtifactsSection(BaseModel):
    artifacts: list[Artifact]


class Header(BaseModel):
    app_name: str
    website: str
    developer_portal_url: str | None
    summary: str


SECTIONS: dict[str, tuple[type[BaseModel], str]] = {
    "record_facts": (FactsSection, "Record the seven difficulty facts and the access stages."),
    "record_steps": (StepsSection, "Record every dev and production step, in order."),
    "record_findings": (FindingsSection, "Record requirements, nuances, blockers, and open questions."),
    "record_artifacts": (ArtifactsSection, "Record the paste-ready artifacts."),
    "record_composio": (ComposioNote, "Record whether Composio has a managed app for this provider, and your recommendation."),
}
FINISH = "finish_guide"


class IncompleteGuide(Exception):
    pass


class GuideBuilder:
    def __init__(self) -> None:
        self._parts: dict[str, BaseModel] = {}

    def record(self, tool: str, data: dict) -> None:
        """Validate one section; raises pydantic.ValidationError for the agent to fix and resend."""
        model, _ = SECTIONS[tool]
        self._parts[tool] = model.model_validate(data)

    def finish(self, data: dict) -> GuideDraft:
        """Assemble the full guide; raises IncompleteGuide or ValidationError, both reported to the agent."""
        header = Header.model_validate(data)
        missing = [t for t in SECTIONS if t not in self._parts]
        if missing:
            raise IncompleteGuide(f"call {', '.join(missing)} before {FINISH}")
        p = self._parts
        return GuideDraft(
            **header.model_dump(),
            **p["record_facts"].model_dump(),
            **p["record_steps"].model_dump(),
            **p["record_findings"].model_dump(),
            **p["record_artifacts"].model_dump(),
            composio=p["record_composio"].model_dump(),
        )
