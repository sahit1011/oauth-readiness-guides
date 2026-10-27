"""Deterministic difficulty tier and time totals, computed from the agent's extracted facts.

The model never picks the tier itself: it reports facts with evidence, and these rules turn them
into a tier, so every app is graded the same way and every tier can say why.
"""

from .schema import Fact, FactKey, MinMax, Step, Tier, TierResult, Totals

# Most severe first. A fact "triggers" a rule when its value equals the trigger value.
_RULES: list[tuple[Tier, FactKey, bool, str]] = [
    ("restricted", "partner_program_required", True, "Access requires acceptance into a gated partner program"),
    ("restricted", "self_serve_registration", False, "You cannot register an app without the provider's involvement"),
    ("high", "security_assessment_required", True, "A third-party security assessment is required"),
    ("moderate", "production_review_required", True, "The provider reviews the app before arbitrary users can connect"),
    ("moderate", "business_verification_required", True, "The provider verifies your business identity"),
    ("moderate", "paid_plan_required", True, "A paid plan or API tier is required"),
    ("easy", "dev_use_without_review", False, "You cannot test with your own account immediately after registering"),
]


def _grade(values: dict[FactKey, bool]) -> tuple[Tier, list[str]]:
    tier: Tier | None = None
    reasons: list[str] = []
    for rule_tier, key, trigger, reason in _RULES:
        if values[key] == trigger:
            reasons.append(reason)
            tier = tier or rule_tier
    return tier or "instant", reasons


def _supported(fact: Fact) -> bool:
    """A value counts as known only when evidence backs it; an inferred value is a guess."""
    return fact.value is not None and fact.claim.status in ("tested", "sourced")


def grade(facts: list[Fact]) -> TierResult:
    """Grade after verification, so claim statuses reflect any downgrades."""
    known = {f.key: f.value for f in facts if _supported(f)}
    unresolved = [f.key for f in facts if not _supported(f)]
    trigger_of = {key: trigger for _, key, trigger, _ in _RULES}

    optimistic, reasons = _grade({**known, **{k: not trigger_of[k] for k in unresolved}})
    pessimistic, _ = _grade({**known, **{k: trigger_of[k] for k in unresolved}})
    # Face value: every stated value counts, evidence or not; only a null falls back to not triggering.
    stated = {f.key: f.value if f.value is not None else not trigger_of[f.key] for f in facts}
    likely, _ = _grade(stated)
    return TierResult(optimistic=optimistic, pessimistic=pessimistic, likely=likely, reasons=reasons, unresolved=unresolved)


def _sum(ranges: list[MinMax]) -> MinMax:
    return MinMax(low=sum(r.low for r in ranges), high=sum(r.high for r in ranges))


def totals(steps: list[Step], facts: list[Fact]) -> Totals:
    dev = [s for s in steps if s.track == "dev"]
    known_waits = [s.wait_days for s in steps if isinstance(s.wait_days, MinMax)]
    # Production waits are sequential gates (e.g. verification, then security assessment).
    wait = _sum(known_waits)

    unknown = [f'The wait after "{s.title}" is unknown' for s in steps if s.wait_days == "unknown"]
    value_of = {f.key: f.value for f in facts}
    review_possible = any(value_of[k] is not False for k in ("production_review_required", "security_assessment_required"))
    if review_possible and wait.high == 0 and not unknown:
        unknown.append("The provider may review the app, but no review wait is stated")
    return Totals(
        dev_effort_minutes=_sum([s.effort_minutes for s in dev]),
        production_effort_minutes=_sum([s.effort_minutes for s in steps]),
        production_wait_days=wait,
        wait_unknown_reasons=unknown,
    )
