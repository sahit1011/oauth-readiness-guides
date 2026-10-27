"""Guide persistence. Every generation is a new version; a curated version outranks newer generated ones.

Curated means a human checked that version against sources or a setup attempt. Live generation only
ever adds versions, so it can never replace what a person reviewed.
"""

import re

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from .schema import Guide

_SCHEMA = [
    """
    create table if not exists guides (
        slug text not null,
        version integer not null,
        guide jsonb not null,
        created_at timestamptz not null default now(),
        primary key (slug, version)
    )
    """,
    # Every version starts uncurated; curation is an explicit later act (mark_curated).
    "alter table guides add column if not exists curated boolean not null default false",
]

_PREFERRED_ORDER = "order by slug, curated desc, version desc"


class StoredGuide(BaseModel):
    version: int
    curated: bool
    guide: Guide


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive a slug from app name {name!r}")
    return slug


def _host(value: str) -> str | None:
    """The bare host if `value` looks like a URL or domain, else None."""
    value = value.strip().lower()
    if "." not in value or " " in value:
        return None
    return re.sub(r"^[a-z]+://", "", value).split("/")[0].removeprefix("www.")


def matches(query: str, guide: Guide) -> bool:
    """Whether a submitted name or website refers to the app this guide covers."""
    host = _host(query)
    if host is not None:
        site = _host(guide.draft.website)
        # A subdomain of the app's site (docs.github.com) is the same app; a parent domain is not.
        return site is not None and (host == site or host.endswith("." + site))
    return re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") in (guide.slug, slugify(guide.draft.app_name))


class Store:
    def __init__(self, database_url: str) -> None:
        self._url = database_url
        with psycopg.connect(self._url) as conn:
            for statement in _SCHEMA:
                conn.execute(statement)

    def save(self, guide: Guide) -> int:
        with psycopg.connect(self._url) as conn:
            # Serializes concurrent saves of one slug so both get distinct versions; released at commit.
            conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (guide.slug,))
            row = conn.execute(
                """
                insert into guides (slug, version, guide)
                select %(slug)s, coalesce(max(version), 0) + 1, %(guide)s from guides where slug = %(slug)s
                returning version
                """,
                {"slug": guide.slug, "guide": Jsonb(guide.model_dump(mode="json"))},
            ).fetchone()
        return row[0]

    def get(self, slug: str, version: int | None) -> StoredGuide | None:
        """That exact version, or with version None the preferred one: latest curated, else latest."""
        with psycopg.connect(self._url) as conn:
            if version is None:
                row = conn.execute(
                    f"select version, curated, guide from guides where slug = %s {_PREFERRED_ORDER} limit 1", (slug,)
                ).fetchone()
            else:
                row = conn.execute(
                    "select version, curated, guide from guides where slug = %s and version = %s", (slug, version)
                ).fetchone()
        return None if row is None else StoredGuide(version=row[0], curated=row[1], guide=row[2])

    def list_preferred(self) -> list[StoredGuide]:
        with psycopg.connect(self._url) as conn:
            rows = conn.execute(f"select distinct on (slug) version, curated, guide from guides {_PREFERRED_ORDER}").fetchall()
        return [StoredGuide(version=r[0], curated=r[1], guide=r[2]) for r in rows]

    def find(self, query: str) -> StoredGuide | None:
        return next((g for g in self.list_preferred() if matches(query, g.guide)), None)

    def mark_curated(self, slug: str, version: int) -> None:
        with psycopg.connect(self._url) as conn:
            updated = conn.execute(
                "update guides set curated = true where slug = %s and version = %s", (slug, version)
            ).rowcount
        if updated != 1:
            raise LookupError(f"no guide {slug} version {version}")
