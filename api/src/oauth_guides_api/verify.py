"""Grounding check: every claim's evidence status must be backed by what our tools actually returned.

The agent can overstate its evidence. This pass is deterministic: a `sourced` claim keeps its
status only if its quote appears in a cited page, and a `tested` claim only if it cites a probe.
Anything else is downgraded to `inferred`, and the downgrade is recorded for the guide.
"""

import re
from collections.abc import Iterator

from .schema import Claim, Downgrade, GuideDraft, Source

# Shorter quotes match too easily by accident (e.g. "OAuth app") to count as support.
MIN_QUOTE_CHARS = 20

_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_TRANSLATE)).strip().lower()


def _claims(draft: GuideDraft) -> Iterator[tuple[str, Claim]]:
    for fact in draft.facts:
        yield f"facts.{fact.key}", fact.claim
    for stage in draft.stages:
        yield f"stages.{stage.audience}", stage.claim
    for i, step in enumerate(draft.steps):
        for claim in step.claims:
            yield f"steps[{i}] {step.title}", claim
    for claim in draft.requirements:
        yield "requirements", claim
    for claim in draft.nuances:
        yield "nuances", claim
    for blocker in draft.blockers:
        for claim in blocker.claims:
            yield f"blockers: {blocker.title}", claim
    yield "composio", draft.composio.claim


def _failure(claim: Claim, sources: dict[str, Source]) -> str | None:
    """Why the claim's status is unsupported, or None if it holds."""
    # Inferred and unknown claims assert no evidence, so there is nothing to check or downgrade.
    if claim.status not in ("tested", "sourced"):
        return None
    missing = [sid for sid in claim.source_ids if sid not in sources]
    if missing:
        return f"cites unknown source ids {missing}"
    cited = [sources[sid] for sid in claim.source_ids]

    if claim.status == "tested":
        if not any(s.kind == "probe" for s in cited):
            return "marked tested but cites no probe result"
        return None

    if claim.status == "sourced":
        if claim.quote is None or len(claim.quote.strip()) < MIN_QUOTE_CHARS:
            return f"marked sourced without a quote of at least {MIN_QUOTE_CHARS} characters"
        quote = _normalize(claim.quote)
        if not any(quote in _normalize(s.text) for s in cited if s.kind == "page"):
            return "quote not found in any cited fetched page"
        return None

    return None


def verify(draft: GuideDraft, sources: list[Source]) -> tuple[GuideDraft, list[Downgrade]]:
    checked = draft.model_copy(deep=True)
    by_id = {s.id: s for s in sources}
    downgrades: list[Downgrade] = []
    for location, claim in _claims(checked):
        reason = _failure(claim, by_id)
        if reason is not None:
            downgrades.append(
                Downgrade(location=location, statement=claim.statement, from_status=claim.status, to_status="inferred", reason=reason)
            )
            claim.status = "inferred"
    return checked, downgrades
