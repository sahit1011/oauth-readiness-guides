"""Score a generated guide against golden facts researched independently from official sources.

The most damaging error is "confidently wrong": the guide states a wrong value and labels it tested or
sourced. It is counted separately, because the evidence labels are what a developer relies on.
"""

from typing import Literal

from pydantic import BaseModel

from .rubric import grade
from .schema import Claim, Fact, FactKey, Guide, Tier

TIER_ORDER: list[Tier] = ["instant", "easy", "moderate", "high", "restricted"]

Outcome = Literal["correct", "wrong", "confidently_wrong", "guide_unknown", "golden_unknown"]


class GoldenFact(BaseModel):
    value: bool | None
    source_url: str | None
    quote: str | None
    note: str | None = None


class GoldenApp(BaseModel):
    slug: str
    name: str
    scopes_assumed: str | None
    facts: dict[FactKey, GoldenFact]


class FactScore(BaseModel):
    key: FactKey
    golden: bool | None
    guide: bool | None
    guide_status: str
    outcome: Outcome


class AppScore(BaseModel):
    slug: str
    facts: list[FactScore]
    golden_tier: Tier | None
    """None when a golden fact is unknown, since the true tier then isn't settled either."""
    guide_likely: Tier
    guide_range: tuple[Tier, Tier]
    likely_tier_correct: bool | None
    golden_tier_in_range: bool | None


def _outcome(golden: bool | None, fact: Fact) -> Outcome:
    if golden is None:
        return "golden_unknown"
    if fact.value is None:
        return "guide_unknown"
    if fact.value == golden:
        return "correct"
    return "confidently_wrong" if fact.claim.status in ("tested", "sourced") else "wrong"


def score(guide: Guide, golden: GoldenApp) -> AppScore:
    by_key = {f.key: f for f in guide.draft.facts}
    facts = [
        FactScore(key=k, golden=g.value, guide=by_key[k].value, guide_status=by_key[k].claim.status, outcome=_outcome(g.value, by_key[k]))
        for k, g in golden.facts.items()
    ]

    golden_tier: Tier | None = None
    if all(g.value is not None for g in golden.facts.values()):
        # Golden facts are evidence-backed by construction, so they are graded as sourced.
        sourced = Claim(statement="golden", status="sourced", source_ids=[], quote=None)
        golden_tier = grade([Fact(key=k, value=g.value, claim=sourced) for k, g in golden.facts.items()]).likely

    tier = guide.tier
    in_range = None
    if golden_tier is not None:
        lo, hi = TIER_ORDER.index(tier.optimistic), TIER_ORDER.index(tier.pessimistic)
        in_range = lo <= TIER_ORDER.index(golden_tier) <= hi
    return AppScore(
        slug=golden.slug,
        facts=facts,
        golden_tier=golden_tier,
        guide_likely=tier.likely,
        guide_range=(tier.optimistic, tier.pessimistic),
        likely_tier_correct=None if golden_tier is None else tier.likely == golden_tier,
        golden_tier_in_range=in_range,
    )
