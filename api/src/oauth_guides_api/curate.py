"""Mark a guide version as curated once a person has checked it against sources or a setup attempt.

    uv run --env-file .env python -m oauth_guides_api.curate <slug> <version>
"""

import argparse

from .llm import require_env
from .store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug")
    parser.add_argument("version", type=int)
    args = parser.parse_args()
    Store(require_env("GUIDES_DATABASE_URL")).mark_curated(args.slug, args.version)
    print(f"{args.slug} version {args.version} is now curated")


if __name__ == "__main__":
    main()
