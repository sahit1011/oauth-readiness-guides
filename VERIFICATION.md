# Verification

What was checked, how, what it found, and what remains unverified. Dates are 2026-10-28 unless
noted. Nothing here is an expected result: every number comes from a command or run listed with it.

## 1. A golden set from official sources

[`api/eval/golden.json`](api/eval/golden.json) records the seven difficulty facts, access stages, and
stated review waits for 8 entries: GitHub, Slack, Gmail, Notion, Spotify, Microsoft (Entra, delegated
`Mail.Read`), LinkedIn open products, and LinkedIn Community Management.

- Built by a research agent restricted to **official provider documentation**, independently of the
  guide-writing agent and its prompts.
- Every value cites a URL and a verbatim quote. All 93 quotes were checked mechanically against the
  fetched page text (whitespace-normalized): 93 matched. Two were re-checked by a second, separate
  fetch of the live pages (Notion Marketplace listing, Google sensitive-scope verification): both found.
- Facts the official docs don't settle are recorded as `null` and excluded from scoring: LinkedIn
  business verification and paid plan for the open products, and the paid plan for Community Management.

| App | Self-serve | Test before review | Production review | Security assessment | Business verification | Paid plan | Partner program |
|---|---|---|---|---|---|---|---|
| GitHub | Yes | Yes | No¹ | No | No | No | No |
| Slack | Yes | Yes | No² | No | No | No | No |
| Gmail (`gmail.readonly` restricted, `gmail.send` sensitive) | Yes | Yes (100 test users) | Yes | Yes (CASA, yearly) | Yes³ | No⁴ | No |
| Notion (public connection) | Yes | Yes | No | No | No | No | No |
| Spotify | Yes | Yes (5 users) | Yes | No | Yes | Yes (owner needs Premium) | Yes |
| Microsoft (`Mail.Read`, delegated) | Yes | Yes | No⁵ | No | No⁵ | No | No⁵ |
| LinkedIn open products | Yes | Yes | No | No | ? | ? | No |
| LinkedIn Community Management | Yes | No | Yes | No | Yes | ? | Yes |

¹ GitHub never reviews the app, but an organization owner must approve it before it can read that
organization's private data, and new organizations have this restriction on by default.
² Any workspace can install an unlisted app without review. Since 2025-05-29, commercial apps outside
the Slack Marketplace are limited to 1 request per minute and 15 objects on `conversations.history`.
³ Google checks the brand and domain ownership, not the legal business.
⁴ The API is free; Google says over-quota use "is planned to incur charges" later in 2026, and the
CASA assessor may charge a fee.
⁵ Microsoft does not review the app, but each customer tenant's consent policy can block apps from
unverified publishers; publisher verification needs a Microsoft AI Cloud Partner Program account.

### Two conflicting public claims, settled

Two claims that circulate in public write-ups conflict with each other. The official sources say:

- **Notion: does a public connection need review?** No. Review applies only to the optional
  Marketplace listing: "your connection can be used via its OAuth flow without being listed"
  ([marketplace listing](https://developers.notion.com/guides/get-started/marketplace-listing)). The
  listing review's stated turnaround is 5–10 business days. No official source supports "4–8 weeks".
  One official page still says the authorization URL "populates after a public connection is
  submitted for review", which reads as stale text; it is recorded rather than ignored.
- **Google sensitive-scope verification: 3–5 or 10 business days?** Both, on official pages. The
  [sensitive-scope page](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification)
  says "typically takes 3-5 business days"; the [verification FAQ](https://support.google.com/cloud/answer/13463817)
  says 10 business days and that estimates "are not guaranteed". A correct guide gives a range.
  Restricted scopes take weeks longer and add a yearly CASA assessment.

## 2. Generated guides scored against the golden set

`uv run --env-file .env python scripts/evaluate.py` scores the stored guide for each golden app. Each
fact is correct, wrong, **confidently wrong** (wrong *and* labeled tested or sourced, the damaging
case), or unknown.

| App | Model | Facts correct | Confidently wrong | Golden tier | Guide's likely tier | Truth inside guide's range |
|---|---|---|---|---|---|---|
| GitHub (local run) | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 7/7 | 0 | Instant | Instant | yes |
| GitHub (production run, live site) | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 7/7 | 0 | Instant | Instant | yes |
| Slack (live site) | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 6/7 | **1** | Instant | Moderate | no |
| Gmail (live site) | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 6/6 (1 left unknown) | 0 | High | High | yes |
| Notion (live site) | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 7/7 | 0 | Instant | Instant | yes |
| Spotify (live site) | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 6/6 (1 left unknown) | 0 | Restricted | Restricted | yes |
| Microsoft (live site)⁶ | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 7/7 | 0 | Instant | Instant | yes |
| LinkedIn open products (live site) | nvidia/nemotron-3.5-super-vl:free (OpenRouter) | 2/3 (2 left unknown) | **1** | ? | Moderate | ? |

Across the live guides: **41/43 scored facts correct, 2 confidently wrong.** The Notion guide settles
the first conflicting claim above correctly: a public connection needs no review.

⁶ The agent named the app "Microsoft identity platform (Azure AD) / Microsoft Graph", so the guide is
stored under a longer slug than the golden entry's `microsoft` and `evaluate.py` reports it as not
generated; it was scored against the `microsoft` entry with the same `score` function.

**The Slack miss, and what it shows.** The guide says Slack reviews an app before arbitrary users can
connect, labeled `sourced`, with a quote the verifier confirmed verbatim on docs.slack.dev: "apps
intended for commercial distribution should be submitted and approved for listing in the Slack
Marketplace. Unlike unlisted distributed apps, apps listed in the Slack Marketplace are reviewed…".
The quote is real, but it describes Marketplace *listing* review, and its second sentence says unlisted
apps are not reviewed, which is the golden answer. This is the verifier's known limit made concrete: it
proves a quote exists, not that the quote supports the statement. The golden value stays as it is.
The case is genuinely nuanced, though: since 2025-05-29 unlisted commercial apps are limited to 1
request per minute on `conversations.history`, so for an agent that reads messages, Marketplace review
is effectively required. A good guide says exactly that. This guide also missed that rate limit, the
most important Slack nuance for agent builders.

The production row comes from `uv run python scripts/evaluate.py --api https://oauth-guides-api.onrender.com`,
which reads guides through the public API, so the production database keeps accepting connections
only from inside Render.

**The LinkedIn miss** is the same kind of mistake. The guide merges LinkedIn's two products: it says
posting scopes such as `w_member_social` need the Community Management access review before anyone can
connect (labeled `sourced`). In the golden set that scope comes with the self-serve "Share on
LinkedIn" product, and the review applies only to the Community Management API. Scored against the
Community Management entry instead, it gets 3/4 with one plain wrong fact. No guide covers the
Community Management API on its own yet.

**What the GitHub result shows.** The free model got every value right, but 13 of the statements it
labeled as sourced did not quote their page verbatim, so the verifier downgraded them and the guide
shows "Likely Instant (unconfirmed)". Correctness and evidence are different things and are measured
separately: a guide can be right for the wrong reasons, and the developer deserves to know which.

## 3. What the verifier caught

The verifier ([`verify.py`](api/src/oauth_guides_api/verify.py)) checks every claim against what the
agent's tools actually returned. From two free-model GitHub runs:

| Run | Statements downgraded | Reasons |
|---|---|---|
| First (single submit call) | 12 | 8 quotes not found in the cited page; 4 "sourced" claims with no usable quote |
| After moving to section-by-section recording | 13 | all 13: quote not found in the cited page |
| Production run on the deployed site | 4 | all 4: quote not found in the cited page. The model labeled 5 of its 7 facts as inferred itself, instead of overclaiming |

Examples (statement, as the agent wrote it, then downgraded to inferred):

- "GitHub does not require review or verification of an OAuth app before arbitrary users can
  authorize it." (true per the golden set, but the cited quote was a paraphrase)
- "Any GitHub user can authorize immediately after registration; no production gate exists."
  (also a paraphrase; and it misses the organization-approval nuance in the golden set)

## 4. What the probes observed first-hand

Unauthenticated probes ([`probes.py`](api/src/oauth_guides_api/probes.py)), run live:

- **GitHub** publishes no OAuth discovery document (`/.well-known/openid-configuration` and
  `/.well-known/oauth-authorization-server` both return 404), and its authorize endpoint redirects to
  the login page before validating the client ID. An unauthenticated probe cannot observe how GitHub
  rejects an unknown app; guides say so instead of implying a test.
- **Google** publishes both discovery documents (PKCE `S256` supported). Its authorize endpoint
  validates parameters before login: without `scope` it returns "Missing required parameter: scope";
  with `scope=openid` it returns "Error 401: invalid_client — The OAuth client was not found". This led
  to the probe taking an optional scope.

## 5. What we changed because of what we found

| Finding | Change |
|---|---|
| A model sent a nested object field (`composio`) as an unparseable JSON string, 13 resubmissions in one run (reproduced 2/2 with a minimal schema) | Tool schemas are inlined, and the guide is recorded in five small validated sections. The next run needed 1 resubmission. |
| Weakly evidenced facts made every guide read "Instant to Restricted" | The face-value tier is shown as "Likely X (unconfirmed)", with the worst case alongside |
| `null` meant both "no wait" and "unknown", so an unknown review wait rendered as "No wait" | Waits are explicitly `none` or `unknown`; if a review may apply and no wait is stated, the guide says "Unknown" |
| The model chooses probe URLs and reads untrusted pages | Probes are restricted to https hosts that resolve only to public addresses, on every redirect |
| Two public analyses disagreed on Notion and Google timelines | Settled from official sources above; the golden set records both Google figures |

## 6. Not verified

- **Console-only facts** (test-user caps on the Audience page, unverified-app warnings, the exact
  registration fields) need a person to go through setup on a free account. The checklist is in
  [docs/setup-attempts.md](docs/setup-attempts.md); those attempts are **pending**.
- **Guides from the primary model (Claude).** All runs so far used the free OpenRouter fallback
  because no funded Claude key was available.
- LinkedIn business verification and paid tiers; GitHub Marketplace publisher verification; how long
  Spotify's partner application and Microsoft's partner verification take.
- The verifier's quote check is lexical: it proves a quote exists in the cited page, not that the page
  supports the statement (the Slack miss above is a real instance), and a `tested` claim is accepted
  when it cites any probe.
- No guide is marked human-reviewed yet: that waits on the setup attempts above.
