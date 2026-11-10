import { connection } from "next/server";
import postgres from "postgres";
import type { Guide, GuideSummary, StoredGuide } from "./types";

// Pages read the library straight from Postgres, so they never wait for the API to wake from idle.
// The API stays the only writer; GUIDES_DATABASE_URL here should be a read-only role.

let client: postgres.Sql | null = null;
// Chosen, not sourced: close a connection after 20 idle seconds. Vercel keeps warm instances around, and an
// open connection can keep Neon's free compute from suspending, which spends its monthly compute hours.
const IDLE_TIMEOUT_SECONDS = 20;
// guides.version is a Postgres `integer` (api/src/oauth_guides_api/store.py); Postgres rejects larger values.
const MAX_VERSION = 2_147_483_647;

// connection() keeps these reads out of the build-time prerender: a driver query is not a `fetch`, so
// Next would otherwise run it once at build and serve that snapshot of the library to every visitor.
async function db(): Promise<postgres.Sql> {
  await connection();
  if (client === null) {
    const url = process.env.GUIDES_DATABASE_URL;
    if (!url) throw new Error("GUIDES_DATABASE_URL is not set");
    client = postgres(url, { idle_timeout: IDLE_TIMEOUT_SECONDS });
  }
  return client;
}

type Row = { version: number; curated: boolean; guide: Guide };

// Same preference as the API's store (api/src/oauth_guides_api/store.py, _PREFERRED_ORDER):
// the latest curated version, else the latest.

export async function listGuides(): Promise<GuideSummary[]> {
  const sql = await db();
  const rows = await sql<Row[]>`
    select distinct on (slug) version, curated, guide from guides order by slug, curated desc, version desc`;
  return rows.map(({ version, curated, guide }) => ({
    slug: guide.slug,
    version,
    curated,
    app_name: guide.draft.app_name,
    website: guide.draft.website,
    summary: guide.draft.summary,
    tier: guide.tier,
    totals: guide.totals,
    generated_at: guide.provenance.generated_at,
  }));
}

/** The preferred version, or exactly `version` (a string of digits, checked by the caller) when given. */
export async function getGuide(slug: string, version: string | null): Promise<StoredGuide | null> {
  if (version !== null && Number(version) > MAX_VERSION) return null;
  const sql = await db();
  const rows =
    version === null
      ? await sql<Row[]>`
          select version, curated, guide from guides where slug = ${slug}
          order by curated desc, version desc limit 1`
      : await sql<Row[]>`
          select version, curated, guide from guides where slug = ${slug} and version = ${Number(version)}`;
  return rows.length === 0 ? null : rows[0];
}
