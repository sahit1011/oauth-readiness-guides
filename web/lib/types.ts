// Mirrors api/src/oauth_guides_api/schema.py and store.py. Keep them in sync when the schema changes.

export type EvidenceStatus = "tested" | "sourced" | "inferred" | "unknown";
export type Owner = "agent" | "agent_prepares" | "human";
export type Track = "dev" | "production";
export type Tier = "instant" | "easy" | "moderate" | "high" | "restricted";
export type Audience = "only_you" | "test_users" | "anyone";

export type Claim = { statement: string; status: EvidenceStatus; source_ids: string[]; quote: string | null };
export type MinMax = { low: number; high: number };
export type Fact = { key: string; value: boolean | null; claim: Claim };

export type Stage = { audience: Audience; who_can_connect: string; user_cap: number | null; unlocked_by: string; claim: Claim };

export type Step = {
  title: string;
  track: Track;
  owner: Owner;
  instructions: string;
  effort_minutes: MinMax;
  wait_days: MinMax | "none" | "unknown";
  claims: Claim[];
};

export type Blocker = { title: string; impact: string; way_forward: string; claims: Claim[] };
export type Artifact = { kind: string; title: string; content: string; language: string | null };

export type GuideDraft = {
  app_name: string;
  website: string;
  developer_portal_url: string | null;
  summary: string;
  facts: Fact[];
  stages: Stage[];
  steps: Step[];
  requirements: Claim[];
  nuances: Claim[];
  blockers: Blocker[];
  artifacts: Artifact[];
  composio: { managed_app_available: boolean | null; claim: Claim; recommendation: string };
  open_questions: string[];
};

export type Source = { id: string; kind: "search" | "page" | "probe"; url: string; title: string; retrieved_at: string; text: string };
export type TierResult = { optimistic: Tier; pessimistic: Tier; likely: Tier; reasons: string[]; unresolved: string[] };
export type Totals = {
  dev_effort_minutes: MinMax;
  production_effort_minutes: MinMax;
  production_wait_days: MinMax;
  wait_unknown_reasons: string[];
};
export type Downgrade = { location: string; statement: string; from_status: EvidenceStatus; to_status: EvidenceStatus; reason: string };

export type Guide = {
  slug: string;
  draft: GuideDraft;
  tier: TierResult;
  totals: Totals;
  sources: Source[];
  downgrades: Downgrade[];
  provenance: { generated_at: string; llm_providers: string[]; models: string[]; query: string };
};

export type StoredGuide = { version: number; curated: boolean; guide: Guide };

export type GenerateResponse = { job_id: string } | { existing: { slug: string; app_name: string; curated: boolean } };

export type GuideSummary = {
  slug: string;
  version: number;
  curated: boolean;
  app_name: string;
  website: string;
  summary: string;
  tier: TierResult;
  totals: Totals;
  generated_at: string;
};

export type JobEvent =
  | { type: "status"; text: string }
  | { type: "note"; text: string }
  | { type: "tool"; name: string; input: Record<string, unknown> }
  | { type: "source"; id: string; kind: Source["kind"]; url: string; title: string }
  | { type: "section"; name: string }
  | { type: "invalid_guide"; error: string }
  | { type: "done"; slug: string; version: number; downgrades: number }
  | { type: "error"; message: string };
