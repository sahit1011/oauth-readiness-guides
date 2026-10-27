import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { CurationBadge, EVIDENCE, OWNER, TierBadge } from "@/components/badges";
import { Callout } from "@/components/Callout";
import { ClaimList, ClaimView, EvidenceDetails } from "@/components/ClaimView";
import { CodeBlock } from "@/components/CodeBlock";
import { CopyButton } from "@/components/CopyButton";
import { headers } from "next/headers";
import { guideToMarkdown } from "@/lib/markdown";
import { ArrowRightIcon, PageIcon, ProbeIcon, SearchIcon } from "@/components/icons";
import { LibrarySidebar } from "@/components/LibrarySidebar";
import { Toc } from "@/components/Toc";
import { getGuide } from "@/lib/api";
import { AUDIENCE_LABEL, FACT_LABEL, TIER_LABEL, TIER_MEANING, approvalWait, days, hostOf, minutes } from "@/lib/format";
import type { EvidenceStatus, Owner, Source, Stage, Step, StoredGuide } from "@/lib/types";

const SECTIONS: [string, string][] = [
  ["overview", "Overview"],
  ["difficulty", "Difficulty and why"],
  ["access", "Who can connect, when"],
  ["development", "Get working in development"],
  ["production", "Get approved for production"],
  ["blockers", "Blockers and how to proceed"],
  ["requirements", "Requirements and nuances"],
  ["artifacts", "Ready-to-use artifacts"],
  ["composio", "Using it with Composio"],
  ["unverified", "What we could not verify"],
  ["sources", "Sources"],
];

const SOURCE_ICON: Record<Source["kind"], (p: { className?: string }) => React.ReactNode> = {
  search: SearchIcon,
  page: PageIcon,
  probe: ProbeIcon,
};
const SOURCE_KIND: Record<Source["kind"], string> = { search: "Web search", page: "Fetched page", probe: "Probe" };

function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="group mb-4 mt-14 text-2xl font-semibold tracking-tight text-zinc-900">
      <a href={`#${id}`} className="no-underline">
        {children}
        <span className="ml-2 text-zinc-300 opacity-0 transition group-hover:opacity-100">#</span>
      </a>
    </h2>
  );
}

function Lead({ children }: { children: React.ReactNode }) {
  return <p className="mb-5 text-[15px] leading-7 text-zinc-600">{children}</p>;
}

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm shadow-zinc-100">
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-1.5 text-xl font-semibold tracking-tight text-zinc-900">{value}</p>
      <p className="mt-1 text-xs leading-5 text-zinc-500">{hint}</p>
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700">
      <span className="text-zinc-500">{label}</span>
      <span className="font-medium text-zinc-900">{value}</span>
    </span>
  );
}

function waitLabel(wait: Step["wait_days"]): string {
  if (wait === "none") return "None";
  if (wait === "unknown") return "Unknown";
  return days(wait);
}

function StepTimeline({ steps }: { steps: Step[] }) {
  if (steps.length === 0) return <p className="text-zinc-600">No steps in this track.</p>;
  return (
    <ol className="relative flex flex-col">
      {steps.map((s, i) => (
        <li key={i} className="relative flex gap-4 pb-8 last:pb-0">
          {i < steps.length - 1 && <span className="absolute left-[13px] top-8 h-[calc(100%-2rem)] w-px bg-zinc-200" aria-hidden />}
          <span className="relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-zinc-300 bg-white text-sm font-semibold text-zinc-800">
            {i + 1}
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-2.5 pt-0.5">
            <h3 className="font-semibold leading-6 text-zinc-900">{s.title}</h3>
            <div className="flex flex-wrap gap-1.5">
              <Chip label="Who" value={OWNER[s.owner].label} />
              <Chip label="Work" value={minutes(s.effort_minutes)} />
              <Chip label="Wait after" value={waitLabel(s.wait_days)} />
            </div>
            <p className="whitespace-pre-wrap text-[15px] leading-7 text-zinc-700">{s.instructions}</p>
            <EvidenceDetails claims={s.claims} />
          </div>
        </li>
      ))}
    </ol>
  );
}

function StageFlow({ stages }: { stages: Stage[] }) {
  const order = { only_you: 0, test_users: 1, anyone: 2 };
  const sorted = [...stages].sort((a, b) => order[a.audience] - order[b.audience]);
  return (
    <div className="flex flex-col items-stretch gap-2 md:flex-row md:items-start">
      {sorted.map((st, i) => (
        <div key={st.audience} className="flex flex-1 flex-col items-stretch gap-2 md:flex-row md:items-start">
          <div className="flex flex-1 flex-col gap-2 rounded-xl border border-zinc-200 bg-white p-4">
            <div className="flex flex-col items-start gap-1">
              <span className="font-semibold text-zinc-900">{AUDIENCE_LABEL[st.audience]}</span>
              {st.user_cap !== null && <span className="rounded-md bg-zinc-100 px-1.5 py-0.5 text-xs font-medium text-zinc-700">Up to {st.user_cap.toLocaleString()} users</span>}
            </div>
            <p className="text-sm leading-6 text-zinc-700">{st.who_can_connect}</p>
            <p className="text-xs leading-5 text-zinc-500">
              <span className="font-medium text-zinc-600">Unlocked by:</span> {st.unlocked_by}
            </p>
            <EvidenceDetails claims={[st.claim]} />
          </div>
          {i < sorted.length - 1 && <ArrowRightIcon className="mx-auto h-5 w-5 shrink-0 rotate-90 self-center text-zinc-400 md:mt-8 md:rotate-0" />}
        </div>
      ))}
    </div>
  );
}

function GuideView({ stored, pageUrl }: { stored: StoredGuide; pageUrl: string }) {
  const guide = stored.guide;
  const d = guide.draft;
  const managed = d.composio.managed_app_available;
  const confirmed = guide.tier.optimistic === guide.tier.pessimistic;
  const shownTier = confirmed ? guide.tier.optimistic : guide.tier.likely;

  return (
    <article className="min-w-0 flex-1">
      <nav className="mb-4 flex items-center gap-1.5 text-sm text-zinc-500">
        <Link href="/" className="hover:text-zinc-900">
          Library
        </Link>
        <span>/</span>
        <span className="text-zinc-700">{d.app_name}</span>
      </nav>

      <h1 id="overview" className="text-4xl font-semibold tracking-tight text-zinc-900">
        {d.app_name}
      </h1>
      <p className="mt-2 text-lg text-zinc-500">OAuth app setup and approval guide</p>
      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <TierBadge tier={guide.tier} />
        <CurationBadge curated={stored.curated} />
        <span className="text-zinc-400">·</span>
        <a href={d.website} className="text-zinc-600 hover:text-zinc-900 hover:underline">
          {hostOf(d.website)}
        </a>
        {d.developer_portal_url && (
          <>
            <span className="text-zinc-400">·</span>
            <a href={d.developer_portal_url} className="text-zinc-600 hover:text-zinc-900 hover:underline">
              Developer portal
            </a>
          </>
        )}
        <span className="text-zinc-400">·</span>
        <span className="text-zinc-500">Version {stored.version}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1 rounded-lg border border-zinc-200 bg-zinc-50 p-1 text-zinc-700 sm:w-fit">
        <CopyButton text={pageUrl} label="Copy link" />
        <CopyButton text={guideToMarkdown(stored, pageUrl)} label="Copy as Markdown" />
        <a
          href={`/apps/${guide.slug}/markdown?v=${stored.version}`}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-200/70 hover:text-zinc-900"
        >
          <PageIcon className="h-3.5 w-3.5" />
          Download .md
        </a>
      </div>

      <p className="mt-6 text-[17px] leading-8 text-zinc-700">{d.summary}</p>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="First test connection" value={minutes(guide.totals.dev_effort_minutes)} hint="Your hands-on time to connect your own account." />
        <Metric label="Work to launch" value={minutes(guide.totals.production_effort_minutes)} hint="All hands-on steps until any user can connect." />
        <Metric
          label="Waiting on provider"
          value={approvalWait(guide.totals)}
          hint={guide.totals.wait_unknown_reasons.length > 0 ? guide.totals.wait_unknown_reasons[0] : "Calendar time you cannot shorten."}
        />
        <Metric
          label="Composio managed app"
          value={managed === null ? "Unknown" : managed ? "Available" : "Not available"}
          hint={managed ? "You can start today without your own app." : "You need to register your own app."}
        />
      </div>

      <div className="mt-6">
        <Callout variant="note" title="How to read this guide">
          <p>
            Every statement carries an evidence label.{" "}
            {(Object.keys(EVIDENCE) as EvidenceStatus[]).map((s, i) => (
              <span key={s}>
                <b>{EVIDENCE[s].label}</b>: {EVIDENCE[s].meaning.toLowerCase()}
                {i < 3 ? " " : ""}
              </span>
            ))}
          </p>
          <p>
            Steps say who does them:{" "}
            {(Object.keys(OWNER) as Owner[]).map((o, i) => (
              <span key={o}>
                <b>{OWNER[o].label}</b> ({OWNER[o].meaning.replace(/\.$/, "").toLowerCase()}){i < 2 ? "; " : "."}
              </span>
            ))}
          </p>
        </Callout>
      </div>

      <H2 id="difficulty">Difficulty and why</H2>
      <Callout variant={shownTier === "instant" || shownTier === "easy" ? "success" : "warning"} title={`${confirmed ? "" : "Likely "}${TIER_LABEL[shownTier]}${confirmed ? "" : " (unconfirmed)"}`}>
        <p>{TIER_MEANING[shownTier]}</p>
        {guide.tier.reasons.length > 0 && (
          <ul className="list-disc pl-5">
            {guide.tier.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
        {!confirmed && (
          <p>
            {guide.tier.unresolved.length} of 7 deciding facts are not confirmed by evidence; if they turn out the other way, this could be as hard as{" "}
            <b>{TIER_LABEL[guide.tier.pessimistic]}</b>.
          </p>
        )}
      </Callout>
      <div className="mt-5 overflow-x-auto rounded-xl border border-zinc-200">
        <table className="w-full border-collapse text-left text-[15px]">
          <thead className="bg-zinc-50 text-xs uppercase tracking-wider text-zinc-500">
            <tr>
              <th className="px-4 py-2.5 font-semibold">Question</th>
              <th className="px-4 py-2.5 font-semibold">Answer</th>
              <th className="px-4 py-2.5 font-semibold">Evidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200">
            {d.facts.map((f) => (
              <tr key={f.key} className="align-top">
                <td className="w-2/5 px-4 py-3 text-zinc-800">{FACT_LABEL[f.key] ?? f.key}</td>
                <td className="px-4 py-3 font-semibold text-zinc-900">{f.value === null ? "Unknown" : f.value ? "Yes" : "No"}</td>
                <td className="px-4 py-3">
                  <ClaimView claim={f.claim} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2 id="access">Who can connect, when</H2>
      <Lead>Each stage widens who can authorize your app, and what you must complete to get there.</Lead>
      <StageFlow stages={d.stages} />

      <H2 id="development">Get working in development</H2>
      <Lead>Connect your own or test accounts. This is usually possible before any provider review.</Lead>
      <StepTimeline steps={d.steps.filter((s) => s.track === "dev")} />

      <H2 id="production">Get approved for production</H2>
      <Lead>What it takes before any of your users can connect.</Lead>
      <StepTimeline steps={d.steps.filter((s) => s.track === "production")} />

      <H2 id="blockers">Blockers and how to proceed</H2>
      <div className="flex flex-col gap-3">
        {d.blockers.length === 0 && <p className="text-zinc-600">No blockers identified.</p>}
        {d.blockers.map((b) => (
          <Callout key={b.title} variant="warning" title={b.title}>
            <p>{b.impact}</p>
            <p>
              <b>How to proceed:</b> {b.way_forward}
            </p>
            <EvidenceDetails claims={b.claims} />
          </Callout>
        ))}
      </div>

      <H2 id="requirements">Requirements and nuances</H2>
      <h3 className="mb-3 font-semibold text-zinc-900">Requirements</h3>
      {d.requirements.length === 0 ? <p className="text-zinc-600">None identified.</p> : <ClaimList claims={d.requirements} />}
      <h3 className="mb-3 mt-8 font-semibold text-zinc-900">Nuances that affect setup</h3>
      {d.nuances.length === 0 ? <p className="text-zinc-600">None identified.</p> : <ClaimList claims={d.nuances} />}

      <H2 id="artifacts">Ready-to-use artifacts</H2>
      <Lead>Values and text the agent prepared for you to paste.</Lead>
      <div className="flex flex-col gap-4">
        {d.artifacts.map((a) => (
          <CodeBlock key={a.title} title={a.title} language={a.language} content={a.content} />
        ))}
      </div>

      <H2 id="composio">Using it with Composio</H2>
      <Callout variant={managed ? "success" : "note"} title={managed ? "A Composio managed app is available" : "Bring your own OAuth app"}>
        <p>{d.composio.recommendation}</p>
      </Callout>
      <div className="mt-3">
        <EvidenceDetails claims={[d.composio.claim]} />
      </div>

      <H2 id="unverified">What we could not verify</H2>
      {d.open_questions.length > 0 && (
        <>
          <h3 className="mb-2 font-semibold text-zinc-900">Open questions</h3>
          <ul className="mb-6 list-disc pl-5 text-[15px] leading-7 text-zinc-700">
            {d.open_questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </>
      )}
      {guide.downgrades.length > 0 && (
        <>
          <h3 className="mb-2 font-semibold text-zinc-900">Downgraded by the automatic check ({guide.downgrades.length})</h3>
          <p className="mb-3 text-[15px] text-zinc-600">The agent marked these as supported, but its evidence did not hold up, so they are shown as Inferred.</p>
          <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 text-sm">
            {guide.downgrades.map((dg, i) => (
              <li key={i} className="flex flex-col gap-0.5 px-4 py-2.5">
                <span className="text-zinc-800">{dg.statement}</span>
                <span className="text-zinc-500">{dg.reason}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {d.open_questions.length === 0 && guide.downgrades.length === 0 && <p className="text-zinc-600">Nothing flagged.</p>}

      <H2 id="sources">Sources</H2>
      <Lead>
        Generated {new Date(guide.provenance.generated_at).toUTCString()} by {guide.provenance.models.join(", ")} for “{guide.provenance.query}”.
      </Lead>
      <ol className="flex flex-col divide-y divide-zinc-100 rounded-xl border border-zinc-200 text-sm">
        {guide.sources.map((s) => {
          const Icon = SOURCE_ICON[s.kind];
          return (
            <li key={s.id} id={`source-${s.id}`} className="flex items-start gap-3 px-4 py-2.5">
              <span className="w-8 shrink-0 font-mono text-xs leading-5 text-zinc-400">{s.id}</span>
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
              <span className="min-w-0 flex-1">
                <span className="text-zinc-500">{SOURCE_KIND[s.kind]} · </span>
                {s.url.startsWith("http") ? (
                  <a href={s.url} className="break-all text-sky-700 hover:underline">
                    {s.title}
                  </a>
                ) : (
                  <span className="text-zinc-800">{s.title}</span>
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </article>
  );
}

async function GuideLoader({ params, searchParams }: PageProps<"/apps/[slug]">) {
  const { slug } = await params;
  const { v } = await searchParams;
  // The API rejects a non-numeric version with 422; for a reader that is simply a missing guide.
  if (v !== undefined && !(typeof v === "string" && /^\d+$/.test(v))) notFound();
  const stored = await getGuide(slug, typeof v === "string" ? v : null);
  if (stored === null) notFound();
  const h = await headers();
  // A share link pins the version shown, so the recipient sees exactly this guide even after regeneration.
  // x-forwarded-proto is set by Vercel's proxy and absent only when serving directly (local dev over http).
  const pageUrl = `${h.get("x-forwarded-proto") ?? "http"}://${h.get("host")}/apps/${slug}?v=${stored.version}`;
  return (
    <>
      <aside className="hidden w-52 shrink-0 lg:block">
        <div className="sticky top-20">
          <LibrarySidebar current={slug} />
        </div>
      </aside>
      <GuideView stored={stored} pageUrl={pageUrl} />
      <aside className="hidden w-52 shrink-0 xl:block">
        <div className="sticky top-20">
          <Toc items={SECTIONS} />
        </div>
      </aside>
    </>
  );
}

export default function Page(props: PageProps<"/apps/[slug]">) {
  return (
    <main className="mx-auto flex w-full max-w-7xl gap-10 px-6 py-10">
      <Suspense fallback={<p className="text-zinc-500">Loading guide…</p>}>
        <GuideLoader params={props.params} searchParams={props.searchParams} />
      </Suspense>
    </main>
  );
}
