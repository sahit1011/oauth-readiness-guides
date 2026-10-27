"""Score stored guides against eval/golden.json and print a Markdown report.

    uv run --env-file .env python scripts/evaluate.py

Scores the preferred version of each guide (latest curated, else latest generated) for every app
that has golden facts. Apps without a stored guide are listed as not generated.
"""

import json
from collections import Counter
from pathlib import Path

from oauth_guides_api.evaluate import GoldenApp, score
from oauth_guides_api.llm import require_env
from oauth_guides_api.store import Store

GOLDEN = Path(__file__).resolve().parents[1] / "eval" / "golden.json"


def main() -> None:
    golden = [GoldenApp.model_validate(a) for a in json.loads(GOLDEN.read_text())["apps"]]
    store = Store(require_env("GUIDES_DATABASE_URL"))

    rows, totals, missing = [], Counter(), []
    for app in golden:
        stored = store.get(app.slug, None)
        if stored is None:
            missing.append(app.name)
            continue
        result = score(stored.guide, app)
        outcomes = Counter(f.outcome for f in result.facts)
        totals.update(outcomes)
        scored = outcomes["correct"] + outcomes["wrong"] + outcomes["confidently_wrong"]
        rows.append(
            f"| {app.name} | v{stored.version}{' (curated)' if stored.curated else ''} | {', '.join(stored.guide.provenance.models)} "
            f"| {outcomes['correct']}/{scored} | {outcomes['confidently_wrong']} | {outcomes['guide_unknown']} "
            f"| {result.golden_tier or '?'} | {result.guide_likely} | {result.guide_range[0]}–{result.guide_range[1]} "
            f"| {'yes' if result.golden_tier_in_range else 'no' if result.golden_tier_in_range is False else '?'} |"
        )
        for f in result.facts:
            if f.outcome in ("wrong", "confidently_wrong"):
                rows.append(f"|  ↳ {f.key} | | | guide {f.guide} ({f.guide_status}) vs golden {f.golden} | {f.outcome} | | | | | |")

    print("| App | Version | Model | Facts correct | Confidently wrong | Guide unknown | Golden tier | Guide likely | Guide range | Truth in range |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    scored = totals["correct"] + totals["wrong"] + totals["confidently_wrong"]
    if scored:
        print(f"\nOverall: {totals['correct']}/{scored} scored facts correct, {totals['confidently_wrong']} confidently wrong.")
    if missing:
        print(f"Not generated yet: {', '.join(missing)}")


if __name__ == "__main__":
    main()
