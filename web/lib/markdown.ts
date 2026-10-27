import { AUDIENCE_LABEL, FACT_LABEL, TIER_LABEL, TIER_MEANING, approvalWait, days, minutes } from "./format";
import type { Claim, StoredGuide, Step } from "./types";

const OWNER_LABEL = { agent: "Agent", agent_prepares: "Agent prepares, you submit", human: "You" } as const;

function claim(c: Claim): string {
  const refs = c.source_ids.length ? ` [${c.source_ids.join(", ")}]` : "";
  const quote = c.status === "sourced" && c.quote ? `\n  > "${c.quote}"` : "";
  return `- **${c.status}**: ${c.statement}${refs}${quote}`;
}

function steps(list: Step[]): string {
  if (list.length === 0) return "_No steps in this track._";
  return list
    .map((s, i) => {
      const wait = s.wait_days === "none" ? "none" : s.wait_days === "unknown" ? "unknown" : days(s.wait_days);
      return [
        `${i + 1}. **${s.title}** (who: ${OWNER_LABEL[s.owner]}; work: ${minutes(s.effort_minutes)}; wait after: ${wait})`,
        "",
        s.instructions
          .split("\n")
          .map((l) => `   ${l}`)
          .join("\n"),
        ...s.claims.map((c) => `   ${claim(c)}`),
      ].join("\n");
    })
    .join("\n\n");
}

/** A self-contained Markdown copy of a guide, for pasting into tickets, docs, or chat. */
export function guideToMarkdown(stored: StoredGuide, pageUrl: string): string {
  const g = stored.guide;
  const d = g.draft;
  const confirmed = g.tier.optimistic === g.tier.pessimistic;
  const tier = confirmed
    ? TIER_LABEL[g.tier.optimistic]
    : `Likely ${TIER_LABEL[g.tier.likely]} (unconfirmed; could be up to ${TIER_LABEL[g.tier.pessimistic]})`;
  const managed = d.composio.managed_app_available;

  return [
    `# ${d.app_name}: OAuth app setup and approval`,
    "",
    `Source: ${pageUrl} (version ${stored.version}, ${stored.curated ? "human-reviewed" : "agent-generated, not human-reviewed"})`,
    "",
    d.summary,
    "",
    "## At a glance",
    "",
    `| | |`,
    `|---|---|`,
    `| Difficulty | ${tier} |`,
    `| First test connection | ${minutes(g.totals.dev_effort_minutes)} |`,
    `| Work to launch | ${minutes(g.totals.production_effort_minutes)} |`,
    `| Waiting on provider | ${approvalWait(g.totals)} |`,
    `| Composio managed app | ${managed === null ? "Unknown" : managed ? "Available" : "Not available"} |`,
    "",
    `Evidence labels: **tested** (observed by a probe), **sourced** (quoted from a fetched page, quote verified), **inferred** (agent reasoning), **unknown**.`,
    "",
    "## Difficulty and why",
    "",
    TIER_MEANING[confirmed ? g.tier.optimistic : g.tier.likely],
    "",
    ...g.tier.reasons.map((r) => `- ${r}`),
    "",
    ...d.facts.map((f) => `- ${FACT_LABEL[f.key] ?? f.key} **${f.value === null ? "Unknown" : f.value ? "Yes" : "No"}** (${f.claim.status}: ${f.claim.statement})`),
    "",
    "## Who can connect, when",
    "",
    ...d.stages.map((s) => `- **${AUDIENCE_LABEL[s.audience]}**${s.user_cap !== null ? ` (up to ${s.user_cap} users)` : ""}: ${s.who_can_connect}. Unlocked by: ${s.unlocked_by}.`),
    "",
    "## Get working in development",
    "",
    steps(d.steps.filter((s) => s.track === "dev")),
    "",
    "## Get approved for production",
    "",
    steps(d.steps.filter((s) => s.track === "production")),
    "",
    "## Blockers and how to proceed",
    "",
    ...(d.blockers.length ? d.blockers.map((b) => `- **${b.title}**: ${b.impact} How to proceed: ${b.way_forward}`) : ["_None identified._"]),
    "",
    "## Requirements",
    "",
    ...(d.requirements.length ? d.requirements.map(claim) : ["_None identified._"]),
    "",
    "## Nuances",
    "",
    ...(d.nuances.length ? d.nuances.map(claim) : ["_None identified._"]),
    "",
    "## Ready-to-use artifacts",
    "",
    ...d.artifacts.flatMap((a) => [`### ${a.title}`, "", "```" + (a.language ?? ""), a.content, "```", ""]),
    "## Using it with Composio",
    "",
    d.composio.recommendation,
    "",
    "## What we could not verify",
    "",
    ...d.open_questions.map((q) => `- ${q}`),
    ...g.downgrades.map((dg) => `- Downgraded to inferred: ${dg.statement} (${dg.reason})`),
    "",
    "## Sources",
    "",
    ...g.sources.map((s) => `- [${s.id}] ${s.kind}: ${s.url}`),
    "",
  ].join("\n");
}
