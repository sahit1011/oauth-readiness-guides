"""Build web/data/catalog.json: every Composio toolkit that authenticates with OAuth.

    uv run --env-file .env python scripts/build_catalog.py

The catalog is the entry point for apps outside the curated library: each row links to live generation,
and `managed` says whether Composio already has an OAuth app for it (the first question a developer has).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from oauth_guides_api.agent import make_composio

OUT = Path(__file__).resolve().parents[2] / "web" / "data" / "catalog.json"
OAUTH_SCHEMES = {"OAUTH2", "OAUTH1"}
# Largest page the toolkits endpoint is asked for; pagination continues via next_cursor.
PAGE_SIZE = 200


def main() -> None:
    composio = make_composio()
    apps, cursor = [], None
    while True:
        page = composio.toolkits.list(limit=PAGE_SIZE, cursor=cursor, sort_by="alphabetically")
        for item in page.items:
            schemes = set(item.auth_schemes or [])
            if not schemes & OAUTH_SCHEMES:
                continue
            apps.append(
                {
                    "slug": item.slug,
                    "name": item.name,
                    "website": item.meta.app_url,
                    "categories": [c.name for c in item.meta.categories],
                    "managed": bool(set(item.composio_managed_auth_schemes or []) & OAUTH_SCHEMES),
                }
            )
        cursor = page.next_cursor
        if not cursor:
            break

    OUT.write_text(
        json.dumps(
            {
                "source": "Composio toolkits API (composio.toolkits.list), filtered to OAuth1/OAuth2 auth schemes",
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "apps": sorted(apps, key=lambda a: a["name"].lower()),
            },
            indent=1,
        )
        + "\n"
    )
    managed = sum(a["managed"] for a in apps)
    print(f"wrote {len(apps)} OAuth toolkits ({managed} with a Composio managed app) to {OUT}")


if __name__ == "__main__":
    main()
