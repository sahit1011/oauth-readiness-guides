"""Runs against a real Postgres: `docker compose up -d` and GUIDES_DATABASE_URL from api/.env."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import psycopg
import pytest
from conftest import draft, source

from oauth_guides_api.rubric import grade, totals
from oauth_guides_api.schema import Guide, Provenance
from oauth_guides_api.store import Store, matches, slugify


@pytest.fixture
def store():
    url = os.environ["GUIDES_DATABASE_URL"]
    slug = f"test-{uuid.uuid4().hex[:8]}"
    yield Store(url), slug
    with psycopg.connect(url) as conn:
        conn.execute("delete from guides where slug = %s", (slug,))


def _guide(slug: str, summary: str, app_name="Example", website="https://example.com") -> Guide:
    d = draft()
    d.summary, d.app_name, d.website = summary, app_name, website
    return Guide(
        slug=slug,
        draft=d,
        tier=grade(d.facts),
        totals=totals(d.steps, d.facts),
        sources=[source("s1", "probe", "HTTP 404")],
        downgrades=[],
        provenance=Provenance(generated_at=datetime.now(UTC), llm_providers=["anthropic"], models=["m"], query="q"),
    )


def _preferred(s: Store, slug: str):
    return [g for g in s.list_preferred() if g.guide.slug == slug]


def test_each_save_is_a_new_version_and_latest_wins(store):
    s, slug = store
    assert s.save(_guide(slug, "first")) == 1
    assert s.save(_guide(slug, "second")) == 2
    assert s.get(slug, None).guide.draft.summary == "second"
    assert [g.guide.draft.summary for g in _preferred(s, slug)] == ["second"]


def test_curated_version_outranks_newer_generated_versions(store):
    s, slug = store
    s.save(_guide(slug, "reviewed"))
    s.mark_curated(slug, 1)
    s.save(_guide(slug, "live run"))
    preferred = s.get(slug, None)
    assert (preferred.version, preferred.curated, preferred.guide.draft.summary) == (1, True, "reviewed")
    assert [(g.version, g.curated) for g in _preferred(s, slug)] == [(1, True)]
    newer = s.get(slug, 2)
    assert (newer.curated, newer.guide.draft.summary) == (False, "live run")


def test_mark_curated_rejects_a_missing_version(store):
    s, slug = store
    with pytest.raises(LookupError, match="version 7"):
        s.mark_curated(slug, 7)


def test_concurrent_saves_of_one_slug_get_distinct_versions(store):
    s, slug = store
    with ThreadPoolExecutor(max_workers=6) as pool:
        versions = list(pool.map(lambda i: s.save(_guide(slug, str(i))), range(6)))
    assert sorted(versions) == [1, 2, 3, 4, 5, 6]


def test_round_trip_preserves_the_guide(store):
    s, slug = store
    guide = _guide(slug, "x")
    s.save(guide)
    assert s.get(slug, None).guide == guide


def test_missing_slug_or_version_is_none(store):
    s, slug = store
    assert s.get("no-such-app-" + uuid.uuid4().hex, None) is None
    s.save(_guide(slug, "x"))
    assert s.get(slug, 99) is None


def test_find_matches_by_name_or_website(store):
    s, slug = store
    s.save(_guide(slug, "x", app_name=f"Acme {slug}", website=f"https://www.{slug}.example"))
    assert s.find(f"{slug}.example").guide.slug == slug
    assert s.find(f"Acme {slug}").guide.slug == slug
    assert s.find(f"other-{slug}.example") is None


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("GitHub", True),
        ("github", True),
        ("github.com", True),
        ("https://www.github.com/settings", True),
        ("docs.github.com", True),
        ("git hub", False),
        ("gitlab.com", False),
        ("com", False),
    ],
)
def test_matches(query, expected):
    guide = _guide("github", "x", app_name="GitHub", website="https://github.com")
    assert matches(query, guide) is expected


def test_parent_domain_does_not_match_a_subdomain_app():
    gmail = _guide("gmail", "x", app_name="Gmail", website="https://mail.google.com")
    assert matches("google.com", gmail) is False
    assert matches("mail.google.com", gmail) is True


@pytest.mark.parametrize(("name", "slug"), [("Google Workspace (Gmail)", "google-workspace-gmail"), ("X / Twitter", "x-twitter")])
def test_slugify(name, slug):
    assert slugify(name) == slug


def test_slugify_rejects_names_without_letters_or_digits():
    with pytest.raises(ValueError, match="cannot derive a slug"):
        slugify("—")
