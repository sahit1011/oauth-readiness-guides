"""The investigating agent: researches a provider through Composio Search, probes it, and submits a GuideDraft.

Every tool result is recorded as a Source and labeled with its id in the tool result, so the model
can cite it and the verifier can later check each claim against exactly what the tool returned.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from composio import Composio
from composio.utils.json_schema import dereference_json_schema
from composio_anthropic import AnthropicProvider
from pydantic import ValidationError

from .llm import LLM, Provider, require_env
from .probes import ProbeResult, probe_authorize_endpoint, probe_oauth_discovery
from .builder import FINISH, SECTIONS, GuideBuilder, Header, IncompleteGuide
from .schema import GuideDraft, Source

# Slugs from https://docs.composio.dev/toolkits/composio_search
WEB_SEARCH = "COMPOSIO_SEARCH_WEB"
FETCH_URL = "COMPOSIO_SEARCH_FETCH_URL_CONTENT"
# Latest composio_search version as listed by the Composio API on 2026-10-28.
COMPOSIO_SEARCH_VERSION = "20260903_00"
# composio_search needs no connected account, so one fixed user id serves every run.
COMPOSIO_USER_ID = "oauth-guide-agent"
# Chosen, not sourced: ~5k tokens per page keeps a dozen fetched pages inside the context window.
PAGE_CHAR_LIMIT = 20_000
# Chosen, not sourced: bounds a live run's latency and cost; raise it if guides come back thin.
MAX_TURNS = 30
# claude-api skill default for streamed requests; adaptive thinking shares this budget with the
# GuideDraft, the largest single output.
MAX_TOKENS = 64_000

Emit = Callable[[dict], None]

SYSTEM_PROMPT = """\
You investigate how a developer gets a provider OAuth app ready for production use, and you produce
a guide for developers building AI agents on Composio. Today is {today}.

Context. A provider OAuth app is the client (client id, secret, redirect URI, scopes) a developer
registers in the provider's developer portal. Composio wraps it in an auth config; each end user who
connects creates a connected account through it. Composio offers managed OAuth apps for some
toolkits; developers bring their own app for branding, extra scopes, dedicated quota, or when no
managed app exists.

What matters most to the developer, in order: whether approval or review gates production use, how
long they will wait (calendar time) versus work (hands-on time), prerequisites that surprise people
(business verification, verified domain, privacy policy, demo video, security assessment, paid tier,
partner program), and what they can do today in development before any approval.

Method:
1. Use {search} to find the provider's own documentation: creating an OAuth app, OAuth endpoints and
   scopes, app review / verification / marketplace publishing policy, and API access pricing or tiers
   if access is gated. Prefer provider-owned domains over blogs and forums.
2. Fetch the most relevant pages with {fetch}, exactly one URL per call. Only fetched pages can
   support a `sourced` claim; search results cannot.
3. Fetch https://docs.composio.dev/toolkits/managed-auth to see whether Composio has a managed app for
   this provider, and find Composio's redirect (callback) URI for custom OAuth apps in Composio docs.
4. Run probe_oauth_discovery on the provider's authorization server host and probe_authorize_endpoint
   on its authorization endpoint. Report what you observed, including when a probe could not observe
   something (e.g. the provider shows a login page before validating the client).
5. Record the guide in sections: record_facts, record_steps, record_findings, record_artifacts and
   record_composio (any order; a rejected section names the problem, so fix and resend just that
   one). Then call finish_guide with the app name, website, developer portal URL, and a 2-4 sentence
   summary. You have at most {max_turns} turns. Every turn must call at least one tool; the
   investigation ends only when finish_guide accepts the guide.

Evidence rules. Every claim has a status:
- tested: observed in a probe result you cite.
- sourced: stated in a fetched page you cite, with `quote` copied verbatim from that page's text
  (at least a full clause). Quotes are checked mechanically; a quote not found verbatim is downgraded.
- inferred: your reasoning without direct support. Say so rather than overstate.
- unknown: you could not determine it.
Cite source ids exactly as given in tool results, e.g. "s3". Put anything you could not settle in
open_questions.

Facts (each must appear exactly once; value null when unknown):
- self_serve_registration: a developer can register the app without contacting the provider.
- dev_use_without_review: right after registering, the developer can authorize with their own or
  test accounts, before any review.
- production_review_required: the provider must review or verify the app before arbitrary users can
  authorize it (for the scopes an agent integration typically needs).
- security_assessment_required: a third-party security assessment is required for those scopes.
- business_verification_required: the provider verifies the developer's business or identity.
- paid_plan_required: a paid plan or API tier is needed to register the app or call the API.
- partner_program_required: access requires acceptance into a gated partner program.

Stages. List who can connect at each level of access the provider has, in order: "only_you" (just
the developer's own account), "test_users" (a limited set you add; give user_cap if the provider
caps it), "anyone" (any user). Include only the levels this provider actually has; unlocked_by says
what must be completed to reach that level (e.g. "publish the app and pass verification").

Steps. Split into track "dev" (working with your own/test accounts) and "production" (any user can
connect). effort_minutes is hands-on time. wait_days is calendar time you cannot shorten after the
step: a {{low, high}} range in days, "none" when there is no wait, or "unknown" when a wait exists
or may exist but you found no duration. Never use "none" for a review whose duration you don't
know. owner: "agent" only for what this agent did or fully can do (research, probes, generating
artifacts); "agent_prepares" when the agent produced values or text the human submits; "human" for
anything needing a login, identity, payment, or legal acceptance. Never claim an agent can create the
provider app or obtain client credentials.

Blockers: what stops or delays the developer, its impact, and a concrete way forward (a workaround
such as starting on Composio's managed app, narrowing scopes to avoid a review tier, or who to contact).

Artifacts: give the developer things they can paste: registration form values (including Composio's
redirect URI if you found it), scope justifications when a review asks for them, an app manifest
when the provider supports one, and a pre-submission checklist when review is required.
"""

_LOCAL_TOOLS = [
    {
        "name": "probe_oauth_discovery",
        "description": "Fetch the OIDC and OAuth 2.0 authorization-server metadata documents for a host and report what is published.",
        "input_schema": {
            "type": "object",
            "properties": {"host": {"type": "string", "description": "Authorization server host, e.g. accounts.google.com"}},
            "required": ["host"],
        },
    },
    {
        "name": "probe_authorize_endpoint",
        "description": "Send an authorization request with a deliberately invalid client id and report the redirects and page the provider returns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "authorize_url": {"type": "string", "description": "The provider's OAuth authorization endpoint URL"},
                "scope": {"type": "string", "description": "A scope to include; some providers reject requests without one before checking the client"},
            },
            "required": ["authorize_url"],
        },
    },
    # Section schemas are inlined: with a bare {"$ref": ...} object property, the OpenRouter model sent
    # that field as a JSON string instead of an object (reproduced 2/2 on 2026-10-28; inlined: 2/2).
    *[
        {"name": name, "description": f"{description} Calling it again replaces the section.", "input_schema": dereference_json_schema(model.model_json_schema())}
        for name, (model, description) in SECTIONS.items()
    ],
    {
        "name": FINISH,
        "description": "Assemble and submit the guide from the recorded sections. Call last, after every record_* tool has succeeded.",
        "input_schema": dereference_json_schema(Header.model_json_schema()),
    },
]


class AgentError(RuntimeError):
    pass


def _strings(value: object) -> list[str]:
    """All string leaves of a tool's JSON output; its shape varies by tool."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


class Investigation:
    def __init__(self, llm: LLM, composio: Composio, http: httpx.Client, emit: Emit) -> None:
        self._llm = llm
        self._composio = composio
        self._http = http
        self._emit = emit
        self.sources: list[Source] = []
        self.providers: list[Provider] = []
        self.models: list[str] = []

    def _record(self, kind: str, url: str, title: str, text: str) -> Source:
        source = Source(id=f"s{len(self.sources) + 1}", kind=kind, url=url, title=title, retrieved_at=datetime.now(UTC), text=text)
        self.sources.append(source)
        self._emit({"type": "source", "id": source.id, "kind": kind, "url": url, "title": title})
        return source

    def _composio_tool(self, name: str, args: dict) -> tuple[str, bool]:
        if name == FETCH_URL:
            # The tool also accepts a bare string. One URL per call keeps one page per source.
            urls = args["urls"] if isinstance(args["urls"], list) else [args["urls"]]
            if len(urls) != 1:
                return f"{FETCH_URL} takes exactly one URL per call here; got {len(urls)}.", True
            args = {**args, "urls": urls, "max_characters": PAGE_CHAR_LIMIT}
        response = self._composio.tools.execute(name, args, user_id=COMPOSIO_USER_ID)
        if not response["successful"]:
            return f"{name} failed: {response['error']}", True
        text = "\n".join(_strings(response["data"]))
        if name == WEB_SEARCH:
            source = self._record("search", f"search:{args['query']}", f"Web search: {args['query']}", text)
        else:
            source = self._record("page", args["urls"][0], args["urls"][0], text)
        return f"[source {source.id}]\n{text}", False

    def _probe(self, result: ProbeResult) -> tuple[str, bool]:
        source = self._record("probe", result.url, result.title, result.text)
        return f"[source {source.id}]\n{result.text}", False

    def _run_tool(self, name: str, args: dict) -> tuple[str, bool]:
        self._emit({"type": "tool", "name": name, "input": args})
        if name == "probe_oauth_discovery":
            return self._probe(probe_oauth_discovery(self._http, args["host"]))
        if name == "probe_authorize_endpoint":
            # scope is optional in the tool schema; absent means the probe sends none.
            return self._probe(probe_authorize_endpoint(self._http, args["authorize_url"], args.get("scope")))
        if name in (WEB_SEARCH, FETCH_URL):
            return self._composio_tool(name, args)
        raise AgentError(f"model called unknown tool {name!r}")

    def run(self, query: str) -> GuideDraft:
        tools = [*self._composio.tools.get(COMPOSIO_USER_ID, tools=[WEB_SEARCH, FETCH_URL]), *_LOCAL_TOOLS]
        system = SYSTEM_PROMPT.format(today=datetime.now(UTC).date(), search=WEB_SEARCH, fetch=FETCH_URL, max_turns=MAX_TURNS)
        messages: list[dict] = [{"role": "user", "content": f"Investigate this app and produce its guide: {query}"}]
        builder = GuideBuilder()

        for _ in range(MAX_TURNS):
            # Claude Sonnet 5.5 rejects forced tool_choice (any/tool), so the prompt requires a tool each turn.
            response, provider = self._llm.create(system=system, tools=tools, messages=messages, max_tokens=MAX_TOKENS)
            if provider not in self.providers:
                self.providers.append(provider)
            if response.model not in self.models:
                self.models.append(response.model)
            if response.stop_reason == "refusal":
                details = response.stop_details
                raise AgentError(f"model declined ({details.category}): {details.explanation}" if details else "model declined")
            if response.stop_reason == "max_tokens":
                raise AgentError(f"model output hit max_tokens={MAX_TOKENS} before finishing a tool call")
            # Appended unchanged, thinking blocks included: the harness must stay append-only.
            messages.append({"role": "assistant", "content": response.content})

            results = []
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    self._emit({"type": "note", "text": block.text})
                if block.type != "tool_use":
                    continue
                if block.name in SECTIONS:
                    try:
                        builder.record(block.name, block.input)
                    except ValidationError as exc:
                        self._emit({"type": "invalid_guide", "error": f"{block.name}: {exc}"})
                        results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": f"Section rejected, fix and resend:\n{exc}"})
                        continue
                    self._emit({"type": "section", "name": block.name})
                    results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": False, "content": "Recorded."})
                    continue
                if block.name == FINISH:
                    try:
                        return builder.finish(block.input)
                    except (ValidationError, IncompleteGuide) as exc:
                        self._emit({"type": "invalid_guide", "error": f"{FINISH}: {exc}"})
                        results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": f"Guide not complete, fix and call again:\n{exc}"})
                        continue
                content, is_error = self._run_tool(block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": is_error, "content": content})
            if not results:
                results = [{"type": "text", "text": f"Continue the investigation with a tool call, or record the sections and call {FINISH} if you are done."}]
            messages.append({"role": "user", "content": results})

        raise AgentError(f"no valid guide submitted within {MAX_TURNS} turns")


def make_composio() -> Composio:
    return Composio(
        api_key=require_env("COMPOSIO_API_KEY"),
        provider=AnthropicProvider(),
        toolkit_versions={"composio_search": COMPOSIO_SEARCH_VERSION},
    )
