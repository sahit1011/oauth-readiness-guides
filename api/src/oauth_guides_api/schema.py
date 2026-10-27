"""The guide contract shared by the agent, the verifier, storage, and the web app.

`GuideDraft` is what the agent submits. `Guide` is what we store and render: the draft plus
everything computed deterministically after it (tier, totals, verification, provenance).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

EvidenceStatus = Literal["tested", "sourced", "inferred", "unknown"]
"""tested: observed by one of our probes. sourced: a fetched page says so (quote required).
inferred: the model's reasoning with no direct support. unknown: we could not determine it."""

Owner = Literal["agent", "agent_prepares", "human"]
Track = Literal["dev", "production"]
"""dev: working against your own/test accounts. production: any user can connect."""

Tier = Literal["instant", "easy", "moderate", "high", "restricted"]

FactKey = Literal[
    "self_serve_registration",
    "dev_use_without_review",
    "production_review_required",
    "security_assessment_required",
    "business_verification_required",
    "paid_plan_required",
    "partner_program_required",
]


class Claim(BaseModel):
    statement: str
    status: EvidenceStatus
    source_ids: list[str]
    quote: str | None
    """Verbatim excerpt from a cited source. Required when status is `sourced`."""


class MinMax(BaseModel):
    low: float = Field(ge=0)
    high: float = Field(ge=0)

    @model_validator(mode="after")
    def _ordered(self) -> "MinMax":
        if self.low > self.high:
            raise ValueError(f"low ({self.low}) > high ({self.high})")
        return self


class Fact(BaseModel):
    key: FactKey
    value: bool | None
    """None means the agent could not determine it; the rubric then reports a tier range."""
    claim: Claim


class Step(BaseModel):
    title: str
    track: Track
    owner: Owner
    instructions: str
    effort_minutes: MinMax
    wait_days: MinMax | Literal["none", "unknown"]
    """Calendar wait after this step that the developer cannot shorten (review queues etc.).
    "none" and "unknown" are distinct so an unknown wait never renders as no wait."""
    claims: list[Claim]


class Stage(BaseModel):
    """A level of access: who can connect, and what the developer must complete to reach it."""

    audience: Literal["only_you", "test_users", "anyone"]
    who_can_connect: str
    user_cap: int | None
    """Maximum number of users at this stage, when the provider caps it."""
    unlocked_by: str
    claim: Claim


class Blocker(BaseModel):
    title: str
    impact: str
    way_forward: str
    claims: list[Claim]


class Artifact(BaseModel):
    kind: Literal["registration_values", "manifest", "scope_justification", "code", "checklist"]
    title: str
    content: str
    language: str | None


class ComposioNote(BaseModel):
    managed_app_available: bool | None
    claim: Claim
    recommendation: str


def check_facts_and_stages(facts: list[Fact], stages: list[Stage]) -> None:
    """Shared by GuideDraft and the record_facts section, so the agent learns of a problem when it records it."""
    keys = [f.key for f in facts]
    expected = set(FactKey.__args__)
    if sorted(keys) != sorted(expected):
        raise ValueError(f"facts must cover each of {sorted(expected)} exactly once, got {keys}")
    audiences = [s.audience for s in stages]
    if not audiences or len(audiences) != len(set(audiences)):
        raise ValueError(f"stages must list each audience at most once and at least one, got {audiences}")


class GuideDraft(BaseModel):
    app_name: str
    website: str
    developer_portal_url: str | None
    summary: str
    facts: list[Fact]
    stages: list[Stage]
    steps: list[Step]
    requirements: list[Claim]
    nuances: list[Claim]
    blockers: list[Blocker]
    artifacts: list[Artifact]
    composio: ComposioNote
    open_questions: list[str]

    @model_validator(mode="after")
    def _facts_and_stages(self) -> "GuideDraft":
        check_facts_and_stages(self.facts, self.stages)
        return self


class Source(BaseModel):
    id: str
    kind: Literal["search", "page", "probe"]
    url: str
    title: str
    retrieved_at: datetime
    text: str
    """What the tool actually returned; the verifier checks quotes against this."""


class TierResult(BaseModel):
    optimistic: Tier
    pessimistic: Tier
    """Equal when every fact is backed by evidence. Otherwise the unconfirmed facts could push it this far."""
    likely: Tier
    """Taking the agent's values at face value, evidence or not; shown labeled as unconfirmed."""
    reasons: list[str]
    unresolved: list[FactKey]


class Totals(BaseModel):
    dev_effort_minutes: MinMax
    production_effort_minutes: MinMax
    production_wait_days: MinMax
    """Sum of the waits that are known; see wait_unknown_reasons before reading it as complete."""
    wait_unknown_reasons: list[str]


class Downgrade(BaseModel):
    location: str
    statement: str
    from_status: EvidenceStatus
    to_status: EvidenceStatus
    reason: str


class Provenance(BaseModel):
    generated_at: datetime
    llm_providers: list[Literal["anthropic", "openrouter"]]
    """Every provider that served at least one turn; openrouter appears only after a fallback."""
    models: list[str]
    """Every model that answered a turn; more than one means a refusal fallback ran."""
    query: str


class Guide(BaseModel):
    slug: str
    draft: GuideDraft
    tier: TierResult
    totals: Totals
    sources: list[Source]
    downgrades: list[Downgrade]
    provenance: Provenance
