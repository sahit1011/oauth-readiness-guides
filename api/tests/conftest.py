from datetime import UTC, datetime

from oauth_guides_api.schema import Claim, ComposioNote, Fact, FactKey, GuideDraft, MinMax, Source, Stage, Step


def claim(status="inferred", source_ids=(), quote=None, statement="a statement") -> Claim:
    return Claim(statement=statement, status=status, source_ids=list(source_ids), quote=quote)


def facts(status="sourced", **values: bool | None) -> list[Fact]:
    """All seven facts with evidence of `status`; unspecified ones take the value that does not raise the tier."""
    benign: dict[FactKey, bool] = {
        "self_serve_registration": True,
        "dev_use_without_review": True,
        "production_review_required": False,
        "security_assessment_required": False,
        "business_verification_required": False,
        "paid_plan_required": False,
        "partner_program_required": False,
    }
    merged = {**benign, **values}
    return [Fact(key=k, value=v, claim=claim(status)) for k, v in merged.items()]


def step(track="dev", effort=(5, 10), wait="none", claims=()) -> Step:
    return Step(
        title=f"{track} step",
        track=track,
        owner="human",
        instructions="do it",
        effort_minutes=MinMax(low=effort[0], high=effort[1]),
        wait_days=wait if isinstance(wait, str) else MinMax(low=wait[0], high=wait[1]),
        claims=list(claims),
    )


def stage(audience="anyone") -> Stage:
    return Stage(audience=audience, who_can_connect="anyone", user_cap=None, unlocked_by="registering", claim=claim())


def draft(steps=(), requirements=(), fact_list=None) -> GuideDraft:
    return GuideDraft(
        app_name="Example",
        website="https://example.com",
        developer_portal_url=None,
        summary="",
        # Inferred facts need no evidence, so they never add downgrades to verifier tests.
        facts=fact_list if fact_list is not None else facts(status="inferred"),
        stages=[stage()],
        steps=list(steps),
        requirements=list(requirements),
        nuances=[],
        blockers=[],
        artifacts=[],
        composio=ComposioNote(managed_app_available=None, claim=claim(), recommendation=""),
        open_questions=[],
    )


def source(id: str, kind: str, text: str) -> Source:
    return Source(id=id, kind=kind, url=f"https://example.com/{id}", title=id, retrieved_at=datetime.now(UTC), text=text)
