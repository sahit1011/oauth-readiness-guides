import pytest
from conftest import facts, step

from oauth_guides_api.rubric import grade, totals


def test_all_benign_facts_grade_instant():
    result = grade(facts())
    assert (result.optimistic, result.pessimistic, result.reasons, result.unresolved) == ("instant", "instant", [], [])


@pytest.mark.parametrize(
    ("overrides", "tier"),
    [
        ({"dev_use_without_review": False}, "easy"),
        ({"production_review_required": True}, "moderate"),
        ({"paid_plan_required": True}, "moderate"),
        ({"security_assessment_required": True, "production_review_required": True}, "high"),
        ({"self_serve_registration": False}, "restricted"),
        ({"partner_program_required": True, "security_assessment_required": True}, "restricted"),
    ],
)
def test_most_severe_known_fact_sets_tier(overrides, tier):
    result = grade(facts(**overrides))
    assert result.optimistic == result.pessimistic == tier


def test_every_triggered_rule_is_listed_as_a_reason():
    result = grade(facts(security_assessment_required=True, production_review_required=True))
    assert result.reasons == [
        "A third-party security assessment is required",
        "The provider reviews the app before arbitrary users can connect",
    ]


def test_unknown_fact_widens_tier_to_a_range():
    result = grade(facts(production_review_required=True, security_assessment_required=None))
    assert (result.optimistic, result.pessimistic) == ("moderate", "high")
    assert result.unresolved == ["security_assessment_required"]


def test_inferred_value_counts_as_unresolved_not_as_known():
    fact_list = facts(production_review_required=True)
    review = next(f for f in fact_list if f.key == "partner_program_required")
    review.value, review.claim.status = True, "inferred"
    result = grade(fact_list)
    assert (result.optimistic, result.pessimistic) == ("moderate", "restricted")
    assert result.unresolved == ["partner_program_required"]
    assert "Access requires acceptance into a gated partner program" not in result.reasons


def test_all_facts_inferred_spans_instant_to_restricted():
    result = grade(facts(status="inferred"))
    assert (result.optimistic, result.pessimistic) == ("instant", "restricted")
    assert len(result.unresolved) == 7


def test_unknown_self_serve_is_pessimistically_restricted():
    result = grade(facts(self_serve_registration=None))
    assert (result.optimistic, result.pessimistic) == ("instant", "restricted")


def test_likely_tier_takes_inferred_values_at_face_value():
    fact_list = facts(status="inferred", production_review_required=True)
    result = grade(fact_list)
    assert (result.optimistic, result.likely, result.pessimistic) == ("instant", "moderate", "restricted")


def test_likely_tier_treats_null_as_not_triggering():
    result = grade(facts(security_assessment_required=None))
    assert (result.optimistic, result.likely, result.pessimistic) == ("instant", "instant", "high")


def test_totals_split_dev_effort_from_production_effort_and_wait():
    steps = [step("dev", (5, 10)), step("production", (30, 60), wait=(3, 5)), step("production", (60, 120), wait=(14, 42))]
    result = totals(steps, facts(production_review_required=True))
    assert result.dev_effort_minutes.model_dump() == {"low": 5, "high": 10}
    assert result.production_effort_minutes.model_dump() == {"low": 95, "high": 190}
    assert result.production_wait_days.model_dump() == {"low": 17, "high": 47}
    assert result.wait_unknown_reasons == []


def test_unknown_step_wait_is_reported_not_counted_as_zero():
    steps = [step("production", wait="unknown"), step("production", wait=(2, 3))]
    result = totals(steps, facts())
    assert result.production_wait_days.model_dump() == {"low": 2, "high": 3}
    assert result.wait_unknown_reasons == ['The wait after "production step" is unknown']


def test_possible_review_with_no_stated_wait_is_flagged():
    for fact_list in (facts(production_review_required=True), facts(security_assessment_required=None)):
        result = totals([step("production", wait="none")], fact_list)
        assert result.wait_unknown_reasons == ["The provider may review the app, but no review wait is stated"]


def test_no_review_and_no_wait_means_no_wait():
    result = totals([step("production", wait="none")], facts())
    assert (result.production_wait_days.high, result.wait_unknown_reasons) == (0, [])
