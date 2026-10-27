import Link from "next/link";
import { Suspense } from "react";
import { CurationBadge, TierBadge } from "@/components/badges";
import { Catalog } from "@/components/Catalog";
import { GenerateProvider } from "@/components/GenerateContext";
import { Generator } from "@/components/Generator";
import catalog from "@/data/catalog.json";
import { PageIcon, ProbeIcon, SearchIcon } from "@/components/icons";
import { listGuides } from "@/lib/api";
import {
  TIER_LABEL,
  TIER_MEANING,
  approvalWait,
  hostOf,
  minutes,
} from "@/lib/format";
import type { Tier } from "@/lib/types";

const STEPS = [
  {
    Icon: SearchIcon,
    title: "Research",
    body: "The agent searches the provider's developer documentation, app review policies, and pricing through Composio Search, and reads the pages that matter.",
  },
  {
    Icon: ProbeIcon,
    title: "Probe",
    body: "It checks the provider's live OAuth endpoints: discovery documents and how the authorize endpoint treats an unknown app.",
  },
  {
    Icon: PageIcon,
    title: "Verify",
    body: "Every quoted source is checked against the page it came from, and the difficulty is computed by fixed rules from the evidence, not guessed.",
  },
];

async function Library() {
  const guides = await listGuides();
  if (guides.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-zinc-300 p-6 text-center text-zinc-600">
        No guides yet. Generate the first one above.
      </p>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {guides.map((g) => (
        <Link
          key={g.slug}
          href={`/apps/${g.slug}`}
          className="group flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm shadow-zinc-100 transition hover:border-zinc-300 hover:shadow-md"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold text-zinc-900 group-hover:underline">
                {g.app_name}
              </h3>
              <p className="text-sm text-zinc-500">{hostOf(g.website)}</p>
            </div>
            <TierBadge tier={g.tier} />
          </div>
          <p className="line-clamp-2 text-sm leading-6 text-zinc-600">
            {g.summary}
          </p>
          <dl className="grid grid-cols-3 gap-2 border-t border-zinc-100 pt-3 text-sm">
            <div>
              <dt className="text-xs text-zinc-500">First connection</dt>
              <dd className="font-medium text-zinc-900">
                {minutes(g.totals.dev_effort_minutes)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-zinc-500">Work to launch</dt>
              <dd className="font-medium text-zinc-900">
                {minutes(g.totals.production_effort_minutes)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-zinc-500">Waiting</dt>
              <dd className="font-medium text-zinc-900">
                {approvalWait(g.totals)}
              </dd>
            </div>
          </dl>
          <div>
            <CurationBadge curated={g.curated} />
          </div>
        </Link>
      ))}
    </div>
  );
}

async function CatalogSection() {
  const guides = await listGuides();
  return <Catalog apps={catalog.apps} inLibrary={guides.map((g) => g.slug)} />;
}

export default function Home() {
  const managed = catalog.apps.filter((a) => a.managed).length;
  return (
    <GenerateProvider>
      <main className="mx-auto flex w-full max-w-5xl flex-col px-6 pb-20">
        <section className="flex flex-col gap-5 py-16">
          <p className="text-sm font-medium text-sky-700">
            For developers building AI agents
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-zinc-900 sm:text-5xl">
            Know what it takes to get your OAuth app approved.
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-zinc-600">
            Before your users can connect an app to your agent, you may need to
            register an OAuth app with the provider and get it approved. Some
            providers take minutes. Others take weeks of review, a security
            assessment, or a partner program. Each guide tells you which, what
            to do next, and how sure we are.
          </p>
          <div className="flex flex-wrap gap-3">
            <a
              href="#generate"
              className="rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-zinc-700"
            >
              Generate a guide
            </a>
            <a
              href="#library"
              className="rounded-lg border border-zinc-300 bg-white px-4 py-2.5 text-sm font-medium text-zinc-800 hover:bg-zinc-50"
            >
              Browse the library
            </a>
          </div>
        </section>

        <section
          id="how-it-works"
          className="grid grid-cols-1 gap-4 border-t border-zinc-200 py-12 md:grid-cols-3"
        >
          {STEPS.map(({ Icon, title, body }) => (
            <div key={title} className="flex flex-col gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50">
                <Icon className="h-5 w-5 text-zinc-700" />
              </span>
              <h2 className="font-semibold text-zinc-900">{title}</h2>
              <p className="text-sm leading-6 text-zinc-600">{body}</p>
            </div>
          ))}
        </section>

        <section id="generate" className="border-t border-zinc-200 py-12">
          <h2 className="text-2xl font-semibold tracking-tight text-zinc-900">
            Generate a guide for any app
          </h2>
          <p className="mt-2 max-w-2xl text-[15px] leading-7 text-zinc-600">
            Enter an app name or website. You can watch the agent work; a guide
            takes a few minutes. If the library already covers the app, you will
            be offered the existing guide first.
          </p>
          <div className="mt-6 rounded-xl border border-zinc-200 bg-zinc-50/60 p-5">
            <Generator />
          </div>
        </section>

        <section id="library" className="border-t border-zinc-200 py-12">
          <h2 className="text-2xl font-semibold tracking-tight text-zinc-900">
            Library
          </h2>
          <p className="mb-6 mt-2 text-[15px] text-zinc-600">
            Ready-to-use guides. Human-reviewed guides were checked against
            sources or a real setup attempt.
          </p>
          <Suspense fallback={<p className="text-zinc-500">Loading guides…</p>}>
            <Library />
          </Suspense>

          <h3 className="mb-3 mt-12 font-semibold text-zinc-900">
            Difficulty levels
          </h3>
          <dl className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 text-sm">
            {(Object.keys(TIER_LABEL) as Tier[]).map((t) => (
              <div key={t} className="flex gap-4 px-4 py-2.5">
                <dt className="w-24 shrink-0 font-medium text-zinc-900">
                  {TIER_LABEL[t]}
                </dt>
                <dd className="text-zinc-600">{TIER_MEANING[t]}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section id="catalog" className="border-t border-zinc-200 py-12">
          <h2 className="text-2xl font-semibold tracking-tight text-zinc-900">
            All OAuth apps on Composio
          </h2>
          <p className="mb-6 mt-2 max-w-3xl text-[15px] leading-7 text-zinc-600">
            {catalog.apps.length} Composio toolkits authenticate with OAuth.{" "}
            {managed} have a Composio managed OAuth app, so you can start today
            and bring your own app later for branding, custom scopes, or your
            own rate limits. The other {catalog.apps.length - managed} need your
            own app from day one. Generate a guide for any of them.
          </p>
          <Suspense
            fallback={<p className="text-zinc-500">Loading catalog…</p>}
          >
            <CatalogSection />
          </Suspense>
          <p className="mt-3 text-xs text-zinc-500">
            Source: {catalog.source}, generated{" "}
            {catalog.generated_at.slice(0, 10)}.
          </p>
        </section>
      </main>
    </GenerateProvider>
  );
}
