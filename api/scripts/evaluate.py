"""Score stored guides against eval/golden.json and print a Markdown report.

    uv run --env-file .env python scripts/evaluate.py                                   # local database
    uv run python scripts/evaluate.py --api https://oauth-guides-api.onrender.com       # deployed app

Scores the preferred version of each guide (latest curated, else latest generated) for every app
that has golden facts. Apps without a stored guide are listed as not generated. --api reads guides
through the public API, so the production database never has to accept outside connections.
"""

import argparse
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import httpx

from oauth_guides_api.evaluate import GoldenApp, score
from oauth_guides_api.llm import require_env
from oauth_guides_api.store import Store, StoredGuide

GOLDEN = Path(__file__).resolve().parents[1] / "eval" / "golden.json"
# A Render free instance can take about a minute to wake from idle.
API_TIMEOUT_SECONDS = 90


def _from_api(base_url: str) -> Callable[[str], StoredGuide | None]:
    base_url = base_url.rstrip("/")
    # Checked once up front: a wrong base URL would otherwise 404 every guide and read as "not generated".
    listing = httpx.get(f"{base_url}/api/guides", timeout=API_TIMEOUT_SECONDS)
    if listing.status_code != 200 or not isinstance(listing.json(), list):
        raise SystemExit(f"--api {base_url}: GET /api/guides returned HTTP {listing.status_code}, not a guide list")

    def load(slug: str) -> StoredGuide | None:
        response = httpx.get(f"{base_url}/api/guides/{slug}", timeout=API_TIMEOUT_SECONDS)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return StoredGuide.model_validate(response.json())

    return load


def _from_database(store: Store) -> Callable[[str], StoredGuide | None]:
    def load(slug: str) -> StoredGuide | None:
        return store.get(slug, None)

    return load


def main() -> None:
    parser = argparse.ArgumentParser(description="Score stored guides against eval/golden.json")
    parser.add_argument("--api", metavar="URL", help="read guides from this API instead of GUIDES_DATABASE_URL")
    args = parser.parse_args()
    load = _from_api(args.api) if args.api else _from_database(Store(require_env("GUIDES_DATABASE_URL")))

    golden = [GoldenApp.model_validate(a) for a in json.loads(GOLDEN.read_text())["apps"]]
    rows, totals, missing = [], Counter(), []
    for app in golden:
        stored = load(app.slug)
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
