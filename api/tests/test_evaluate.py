from datetime import UTC, datetime

from conftest import draft, facts

from oauth_guides_api.evaluate import GoldenApp, GoldenFact, score
from oauth_guides_api.rubric import grade, totals
from oauth_guides_api.schema import Guide, Provenance

BENIGN = {
    "self_serve_registration": True,
    "dev_use_without_review": True,
    "production_review_required": False,
    "security_assessment_required": False,
    "business_verification_required": False,
    "paid_plan_required": False,
    "partner_program_required": False,
}


def _golden(**overrides) -> GoldenApp:
    values = {**BENIGN, **overrides}
    return GoldenApp(slug="x", name="X", scopes_assumed=None, facts={k: GoldenFact(value=v, source_url="u", quote="q") for k, v in values.items()})


def _guide(fact_list) -> Guide:
    d = draft(fact_list=fact_list)
    return Guide(
        slug="x",
        draft=d,
        tier=grade(d.facts),
        totals=totals(d.steps, d.facts),
        sources=[],
        downgrades=[],
        provenance=Provenance(generated_at=datetime.now(UTC), llm_providers=["anthropic"], models=["m"], query="q"),
    )


def _outcomes(result):
    return {f.key: f.outcome for f in result.facts if f.outcome != "correct"}


def test_matching_guide_scores_all_correct_and_tier_confirmed():
    result = score(_guide(facts(production_review_required=True)), _golden(production_review_required=True))
    assert _outcomes(result) == {}
    assert (result.golden_tier, result.likely_tier_correct, result.golden_tier_in_range) == ("moderate", True, True)


def test_wrong_value_with_sourced_label_is_confidently_wrong():
    result = score(_guide(facts(status="sourced")), _golden(production_review_required=True))
    assert _outcomes(result) == {"production_review_required": "confidently_wrong"}
    assert (result.likely_tier_correct, result.golden_tier_in_range) == (False, False)


def test_wrong_value_marked_inferred_is_plain_wrong_and_range_can_still_cover_truth():
    result = score(_guide(facts(status="inferred")), _golden(production_review_required=True))
    assert _outcomes(result) == {"production_review_required": "wrong"}
    assert result.guide_range == ("instant", "restricted")
    assert (result.likely_tier_correct, result.golden_tier_in_range) == (False, True)


def test_unknown_on_either_side_is_not_scored_as_right_or_wrong():
    golden = _golden()
    golden.facts["paid_plan_required"].value = None
    result = score(_guide(facts(security_assessment_required=None)), golden)
    assert _outcomes(result) == {"security_assessment_required": "guide_unknown", "paid_plan_required": "golden_unknown"}
    assert (result.golden_tier, result.likely_tier_correct, result.golden_tier_in_range) == (None, None, None)
