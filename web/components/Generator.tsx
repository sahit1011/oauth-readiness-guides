"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useGenerate } from "./GenerateContext";
import { apiUrl } from "@/lib/api";
import type { GenerateResponse, JobEvent } from "@/lib/types";
import { CurationBadge } from "./badges";
import { CheckIcon, InfoIcon, PageIcon, ProbeIcon, SearchIcon, SparkIcon, WarningIcon } from "./icons";

const EVENT_TYPES: JobEvent["type"][] = ["status", "note", "tool", "source", "section", "invalid_guide", "done", "error"];

const SECTION_LABEL: Record<string, string> = {
  record_facts: "Recorded the difficulty facts and access stages",
  record_steps: "Recorded the setup steps",
  record_findings: "Recorded requirements, nuances, and blockers",
  record_artifacts: "Recorded paste-ready artifacts",
  record_composio: "Recorded Composio managed-app status",
};

type Line = { Icon: (p: { className?: string }) => React.ReactNode; text: string; tone: string };

function toolLine(name: string, input: Record<string, unknown>): Line {
  const url = Array.isArray(input.urls) ? String(input.urls[0]) : String(input.urls ?? "");
  switch (name) {
    case "COMPOSIO_SEARCH_WEB":
      return { Icon: SearchIcon, text: `Searching: ${String(input.query)}`, tone: "text-zinc-800" };
    case "COMPOSIO_SEARCH_FETCH_URL_CONTENT":
      return { Icon: PageIcon, text: `Reading ${url}`, tone: "text-zinc-800" };
    case "probe_oauth_discovery":
      return { Icon: ProbeIcon, text: `Probing OAuth discovery documents on ${String(input.host)}`, tone: "text-zinc-800" };
    case "probe_authorize_endpoint":
      return { Icon: ProbeIcon, text: `Probing the authorize endpoint ${String(input.authorize_url)}`, tone: "text-zinc-800" };
    default:
      return { Icon: SparkIcon, text: name, tone: "text-zinc-800" };
  }
}

/** One readable line per event; source events are skipped because they repeat the tool call before them. */
function describe(e: JobEvent): Line | null {
  switch (e.type) {
    case "status":
      return { Icon: SparkIcon, text: e.text, tone: "font-medium text-zinc-900" };
    case "note":
      return { Icon: InfoIcon, text: e.text, tone: "text-zinc-500" };
    case "tool":
      return toolLine(e.name, e.input);
    case "source":
      return null;
    case "section":
      return { Icon: CheckIcon, text: SECTION_LABEL[e.name] ?? e.name, tone: "text-zinc-900" };
    case "invalid_guide":
      return { Icon: WarningIcon, text: "A section did not pass validation; the agent is correcting it.", tone: "text-amber-800" };
    case "done":
      return { Icon: CheckIcon, text: `Guide ready. The automatic check downgraded ${e.downgrades} statements.`, tone: "font-medium text-emerald-800" };
    case "error":
      return { Icon: WarningIcon, text: `Failed: ${e.message}`, tone: "text-red-800" };
  }
}

export function Generator() {
  const [query, setQuery] = useState("");
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [existing, setExisting] = useState<Extract<GenerateResponse, { existing: unknown }>["existing"] | null>(null);
  const source = useRef<EventSource | null>(null);
  const { startRef } = useGenerate();

  // Registered for the catalog's "Generate guide" buttons; called from their click handlers, not from render.
  useEffect(() => {
    startRef.current = (q: string) => {
      setQuery(q);
      start(q, false);
    };
  });

  async function start(q: string, regenerate: boolean) {
    source.current?.close();
    setEvents([]);
    setFailure(null);
    setExisting(null);
    setRunning(true);

    let res: Response;
    try {
      res = await fetch(`${apiUrl()}/api/generate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query: q, regenerate }),
      });
    } catch (err) {
      // fetch rejects with a TypeError on network or CORS failure; show it instead of spinning.
      if (!(err instanceof TypeError)) throw err;
      setFailure(`Could not reach the API: ${err.message}`);
      setRunning(false);
      return;
    }
    if (!res.ok) {
      setFailure(`Could not start: HTTP ${res.status} ${await res.text()}`);
      setRunning(false);
      return;
    }
    const body = (await res.json()) as GenerateResponse;
    if ("existing" in body) {
      setExisting(body.existing);
      setRunning(false);
      return;
    }
    const es = new EventSource(`${apiUrl()}/api/jobs/${body.job_id}/events`);
    source.current = es;
    // The server replays a job's events from the start on every connection, including reconnects.
    es.onopen = () => {
      setEvents([]);
      setFailure(null);
    };
    for (const type of EVENT_TYPES) {
      es.addEventListener(type, (msg) => {
        // "error" is also the name of EventSource's own connection-failure event, which carries no data.
        if (!(msg instanceof MessageEvent)) {
          // CLOSED means the browser gave up (e.g. a 404 because the API restarted and lost the job).
          if (es.readyState === EventSource.CLOSED) {
            setFailure("The job is no longer available on the API. Start the generation again.");
            setRunning(false);
          } else {
            setFailure("Lost connection to the API; reconnecting.");
          }
          return;
        }
        const event = JSON.parse(msg.data) as JobEvent;
        setEvents((prev) => [...prev, event]);
        if (event.type === "done" || event.type === "error") {
          es.close();
          setRunning(false);
        }
      });
    }
  }

  const done = events.find((e): e is Extract<JobEvent, { type: "done" }> => e.type === "done");

  return (
    <section className="flex flex-col gap-3">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          start(query, false);
        }}
        className="flex flex-col gap-2 sm:flex-row"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="App name or website, e.g. Linear or linear.app"
          minLength={2}
          maxLength={200}
          required
          className="flex-1 rounded-lg border border-zinc-300 bg-white px-3.5 py-2.5 text-zinc-900 shadow-sm outline-none placeholder:text-zinc-400 focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200"
        />
        <button disabled={running} className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50">
          {running ? "Investigating…" : "Generate guide"}
        </button>
      </form>
      {failure && <p className="text-sm text-red-800">{failure}</p>}
      {existing && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-sky-200 bg-sky-50/60 px-4 py-3 text-sm text-zinc-900">
          <span>
            Already in the library:{" "}
            <Link href={`/apps/${existing.slug}`} className="font-medium text-sky-800 hover:underline">
              {existing.app_name}
            </Link>
          </span>
          <CurationBadge curated={existing.curated} />
          <button onClick={() => start(query, true)} className="ml-auto rounded-md border border-zinc-300 bg-white px-2.5 py-1 font-medium hover:bg-zinc-50">
            Generate a fresh version anyway
          </button>
        </div>
      )}
      {events.length > 0 && (
        <ol className="flex max-h-[28rem] flex-col gap-2 overflow-y-auto rounded-lg border border-zinc-200 bg-white p-4 text-sm">
          {events.map((e, i) => {
            const line = describe(e);
            if (line === null) return null;
            return (
              <li key={i} className={`flex items-start gap-2.5 leading-6 ${line.tone}`}>
                <line.Icon className="mt-1 h-4 w-4 shrink-0 text-zinc-400" />
                <span className="min-w-0 break-words">{line.text}</span>
              </li>
            );
          })}
          {running && <li className="pl-6 text-zinc-400">Working…</li>}
        </ol>
      )}
      {done && (
        <Link
          href={`/apps/${done.slug}?v=${done.version}`}
          className="self-start rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700"
        >
          Open the guide →
        </Link>
      )}
    </section>
  );
}
