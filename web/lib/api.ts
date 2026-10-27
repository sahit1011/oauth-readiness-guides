import type { GuideSummary, StoredGuide } from "./types";

export function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error("NEXT_PUBLIC_API_URL is not set");
  return url;
}

export async function listGuides(): Promise<GuideSummary[]> {
  const res = await fetch(`${apiUrl()}/api/guides`);
  if (!res.ok) throw new Error(`GET /api/guides failed: HTTP ${res.status}`);
  return res.json();
}

/** The preferred version (latest curated, else latest), or exactly `version` when given. */
export async function getGuide(slug: string, version: string | null): Promise<StoredGuide | null> {
  const query = version === null ? "" : `?v=${encodeURIComponent(version)}`;
  const res = await fetch(`${apiUrl()}/api/guides/${encodeURIComponent(slug)}${query}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET /api/guides/${slug} failed: HTTP ${res.status}`);
  return res.json();
}
