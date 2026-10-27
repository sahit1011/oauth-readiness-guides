# OAuth Readiness Guides

How hard is it to get a provider OAuth app ready so your agent's users can connect? This project
answers that per app, with a library of guides and an agent that researches any app you name and
writes a guide while you watch. Every statement in a guide is labeled **tested**, **sourced**,
**inferred**, or **unknown**, and the labels are checked mechanically rather than taken on the agent's word.

- Live app: https://oauth-readiness-guides-six.vercel.app (web on Vercel)
- API: https://oauth-guides-api.onrender.com/api/guides (FastAPI on Render, with Render Postgres)
- How the guidance was checked: [VERIFICATION.md](VERIFICATION.md)

The API runs on Render's free tier, which stops idle services: the first request after a quiet
period takes about a minute while it wakes up.

The deployed agent currently runs on a free OpenRouter model (no Claude key is configured), which
allows about 50 model requests a day, roughly two new guides. Live generation is also limited to 3
runs at a time and 5 per visitor per hour. Once the daily model quota is used, new generations fail
with a rate-limit error until it resets at 00:00 UTC; the existing library is unaffected.

## The problem

A **provider OAuth app** is the client you register in a provider's developer portal: client ID,
secret, redirect URI, scopes. In Composio it sits inside an **auth config**, and every end user who
connects creates a **connected account** through it. Composio runs managed OAuth apps for some
toolkits, so a developer can start without registering anything; teams bring their own app for
their own consent-screen branding, extra scopes, dedicated rate limits, or because no managed app
exists.

Measured from the Composio toolkits API on 2026-10-27 UTC ([`scripts/build_catalog.py`](api/scripts/build_catalog.py)):
**259 toolkits authenticate with OAuth, and 124 of them have a Composio managed app.** For the other
135, the developer needs their own OAuth app from day one.

Registering the app is rarely the hard part; it usually takes minutes. What surprises developers is
everything around it:

- **Approval gates and calendar time.** App review, verification, security assessments, partner
  programs. Hands-on work of an hour can sit behind weeks of waiting.
- **Hidden prerequisites.** A verified domain, a privacy policy, a demo video, business
  verification, a paid API tier.
- **"Works for me" is not "works for my users".** Many providers let you test immediately with your
  own account or a capped list of test users, and gate everyone else behind review. Developers often
  discover this the week they want to launch.

## What a guide answers

Each guide is organized around the questions above, not around the provider's documentation:

| Question | Where it is answered |
|---|---|
| How difficult is this, and why? | A difficulty level computed by fixed rules from seven facts, each with evidence |
| How long will it take? | Hands-on time to a first test connection, hands-on time to launch, and calendar time waiting on the provider, kept separate |
| Who can connect, when? | Stages: only you → a capped set of test users → anyone, and what unlocks each |
| What do I do next? | Ordered steps for development and for production, each saying who does it |
| What could block me? | Blockers with a concrete way forward |
| What can an agent do for me? | Each step is owned by the agent, prepared by the agent for you to submit, or yours alone; plus paste-ready artifacts |
| How sure is this? | Evidence label on every statement, verified quotes, and a "what we could not verify" section |

## How it works

```
 name or website
       │
       ▼
 ┌─────────────┐   Composio Search (web search, page fetch)   ┌───────────────┐
 │ Agent loop  │ ───────────────────────────────────────────▶ │ Provider docs │
 │ Claude, or  │   probes: OIDC discovery, authorize endpoint  │ OAuth servers │
 │ OpenRouter  │ ───────────────────────────────────────────▶ │               │
 └─────┬───────┘                                               └───────────────┘
       │ records the guide section by section (facts, steps, findings, artifacts, Composio)
       ▼
 ┌─────────────┐   quotes must appear verbatim in the cited page; "tested" must cite a probe
 │ Verifier    │   anything unsupported is downgraded to "inferred", and the downgrade is shown
 └─────┬───────┘
       ▼
 ┌─────────────┐   difficulty from 7 facts by fixed rules; weakly supported facts widen it to a range
 │ Rubric      │   totals keep effort and waiting separate; an unknown wait is never shown as "none"
 └─────┬───────┘
       ▼
 Postgres (versioned; human-reviewed versions outrank generated ones) ──▶ Next.js guide pages
```

Live progress streams to the browser over server-sent events while the agent works.

- `api/`: FastAPI service. Agent ([`agent.py`](api/src/oauth_guides_api/agent.py)), probes
  ([`probes.py`](api/src/oauth_guides_api/probes.py)), verifier ([`verify.py`](api/src/oauth_guides_api/verify.py)),
  rubric ([`rubric.py`](api/src/oauth_guides_api/rubric.py)), guide schema ([`schema.py`](api/src/oauth_guides_api/schema.py)),
  storage ([`store.py`](api/src/oauth_guides_api/store.py)), evaluation ([`evaluate.py`](api/src/oauth_guides_api/evaluate.py)).
- `web/`: Next.js app. Library, live generator, the OAuth app catalog, and the guide pages with
  share link and Markdown export.

## Key decisions

1. **The difficulty level is computed, never chosen by the model.** The agent reports seven facts
   (self-serve registration, testable before review, production review, security assessment,
   business verification, paid tier, partner program). Fixed rules turn them into Instant, Easy,
   Moderate, High, or Restricted, so 100 guides are graded the same way and each level can say why.
2. **Evidence is per statement and checked mechanically.** A `sourced` claim must carry a quote that
   appears verbatim in a page the agent actually fetched; search snippets don't count. A `tested`
   claim must cite a probe. Failures are downgraded to `inferred` and listed on the guide. Facts
   that are only inferred widen the difficulty into "Likely X (unconfirmed), could be up to Y".
3. **Probes make "tested" real without credentials.** The agent fetches the provider's OAuth
   discovery documents and sends an authorization request with a deliberately invalid client ID,
   recording what the provider actually does.
4. **Effort and waiting are separate numbers, and "unknown" is a value.** "45 minutes of work, then
   2–6 weeks of review" is what a developer can plan around. If review may apply but no duration is
   found, the guide says "Unknown", not "No wait".
5. **Human-reviewed versions are protected.** Every generation is a new version. A version a person
   checked outranks newer generated ones, and live generation looks in the library first.
6. **A catalog instead of 100 unreviewed guides.** All 259 OAuth toolkits are listed with their
   managed-app status and a one-click "Generate guide", rather than a batch of guides nobody checked.
7. **The guide is recorded in sections.** A single large submit call made a model emit malformed JSON
   for a nested field (13 resubmissions in one run). Recording facts, steps, findings, artifacts, and
   the Composio note as separate validated calls fixed that and gives the live view a milestone per section.
8. **Probes are confined to the public internet.** Probe targets come from the model, so every
   request and redirect must be https to a host that resolves only to public addresses.

## Running it locally

Prerequisites: Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 20.9+ (Next.js 16 requires it), Docker.

```bash
docker compose up -d                       # Postgres for development

cd api
cp .env.example .env                       # fill in the keys below
uv sync
uv run --env-file .env pytest -q           # unit tests + store tests against the dev database
uv run --env-file .env uvicorn oauth_guides_api.app:app --port 8000

cd ../web
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install
npm run dev                                # http://localhost:3000
```

`api/.env`:

| Variable | Purpose |
|---|---|
| `GUIDES_ANTHROPIC_API_KEY` | Claude for the agent. If unset, every turn goes to OpenRouter. Prefixed so a shell-wide `ANTHROPIC_API_KEY` can't override it. |
| `OPENROUTER_API_KEY` | Fallback provider (outages, or no Claude key) |
| `COMPOSIO_API_KEY` | Composio project key, for the search tools and the catalog |
| `GUIDES_DATABASE_URL` | Postgres connection string |
| `WEB_ORIGIN` | The web app's origin, for CORS |

Useful scripts (run from `api/`):

```bash
uv run --env-file .env python scripts/build_catalog.py      # refresh web/data/catalog.json from Composio
uv run --env-file .env python scripts/evaluate.py           # score stored guides against eval/golden.json
uv run python scripts/evaluate.py --api https://oauth-guides-api.onrender.com   # same, for the deployed app
uv run --env-file .env python -m oauth_guides_api.curate <slug> <version>   # mark a reviewed version
```

## Limitations

- **Single API instance.** Live jobs and rate limits are held in memory, so a restart drops running
  jobs. Fine for a demo; a queue would replace it in production.
- **Free hosting tiers.** The Render free instance sleeps when idle (slow first request), and the
  free Render Postgres database expires on 2026-11-26.
- **The quote check is lexical.** It proves the quote exists in the page, not that the page means
  what the claim says. A `tested` claim is accepted if it cites any probe, without checking that the
  probe output supports the statement.
- **Probes see only the public surface.** Console-only facts (test-user caps, warning screens) need
  a human setup attempt; see [docs/setup-attempts.md](docs/setup-attempts.md).
- **Guide quality depends on the model.** Guides generated through the free OpenRouter fallback had
  many paraphrased "quotes" that the verifier downgraded. Each guide records the models that wrote it.
- **The probe allowlist resolves DNS separately from the connection,** so a DNS-rebinding host could
  still reach an internal address. Acceptable for unauthenticated GET probes; noted rather than hidden.
