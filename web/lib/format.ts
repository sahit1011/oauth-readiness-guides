import type { Audience, MinMax, Tier, Totals } from "./types";

function range(low: number, high: number, unit: string): string {
  const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
  return low === high ? `${fmt(low)} ${unit}` : `${fmt(low)}–${fmt(high)} ${unit}`;
}

export function minutes({ low, high }: MinMax): string {
  if (high < 120) return range(low, high, "min");
  return range(low / 60, high / 60, "h");
}

export function days({ low, high }: MinMax): string {
  if (high === 0) return "No wait";
  if (high < 14) return range(low, high, "days");
  return range(low / 7, high / 7, "weeks");
}

/** Known waits plus an explicit marker when any wait is unknown, so an unknown never reads as "no wait". */
export function approvalWait(totals: Totals): string {
  const unknown = totals.wait_unknown_reasons.length > 0;
  if (!unknown) return days(totals.production_wait_days);
  if (totals.production_wait_days.high === 0) return "Unknown";
  return `${days(totals.production_wait_days)} + unknown`;
}

export const TIER_LABEL: Record<Tier, string> = {
  instant: "Instant",
  easy: "Easy",
  moderate: "Moderate",
  high: "High",
  restricted: "Restricted",
};

export const TIER_MEANING: Record<Tier, string> = {
  instant: "Register and connect any user yourself, with no provider review.",
  easy: "Self-serve, but something delays your first test connection.",
  moderate: "The provider reviews or verifies the app before arbitrary users can connect.",
  high: "A third-party security assessment is required.",
  restricted: "Gated: a partner program, or no self-serve registration.",
};

export const AUDIENCE_LABEL: Record<Audience, string> = {
  only_you: "Only you",
  test_users: "Test users",
  anyone: "Anyone",
};

export const FACT_LABEL: Record<string, string> = {
  self_serve_registration: "Can you register the app yourself?",
  dev_use_without_review: "Can you test with your own account right away?",
  production_review_required: "Does the provider review the app before any user can connect?",
  security_assessment_required: "Is a third-party security assessment required?",
  business_verification_required: "Does the provider verify your business?",
  paid_plan_required: "Is a paid plan or API tier required?",
  partner_program_required: "Is a gated partner program required?",
};

export function hostOf(url: string): string {
  return url.replace(/^[a-z]+:\/\//i, "").split("/")[0].replace(/^www\./, "");
}
