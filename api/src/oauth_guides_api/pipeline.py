from datetime import UTC, datetime

from composio import Composio

from .agent import Emit, Investigation
from .probes import make_probe_client
from .llm import LLM
from .rubric import grade, totals
from .schema import Guide, Provenance
from .store import Store, slugify
from .verify import verify


def generate(query: str, *, llm: LLM, composio: Composio, store: Store, emit: Emit) -> Guide:
    emit({"type": "status", "text": f"Investigating {query}"})
    with make_probe_client() as http:
        investigation = Investigation(llm, composio, http, emit)
        draft = investigation.run(query)

    emit({"type": "status", "text": "Checking every quote against the pages it cites"})
    checked, downgrades = verify(draft, investigation.sources)
    guide = Guide(
        slug=slugify(checked.app_name),
        draft=checked,
        tier=grade(checked.facts),
        totals=totals(checked.steps, checked.facts),
        sources=investigation.sources,
        downgrades=downgrades,
        provenance=Provenance(
            generated_at=datetime.now(UTC),
            llm_providers=investigation.providers,
            models=investigation.models,
            query=query,
        ),
    )
    version = store.save(guide)
    emit({"type": "done", "slug": guide.slug, "version": version, "downgrades": len(downgrades)})
    return guide
