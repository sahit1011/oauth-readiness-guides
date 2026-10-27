"""Unauthenticated checks the agent runs against a provider to observe behavior first-hand.

Each probe returns what it saw as plain text. A claim backed by a probe is `tested`, not
`sourced`, because we observed it instead of reading it in documentation.
"""

import ipaddress
import json
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlencode, urlsplit

import httpx

# Deliberately invalid client id: the probe must never resemble a real app's traffic.
PROBE_CLIENT_ID = "oauth-guide-probe-invalid-client"
PROBE_REDIRECT_URI = "https://example.com/oauth/callback"
# Enough visible text to show the provider's error message without dumping a whole login page.
_TEXT_LIMIT = 1500
_DISCOVERY_KEYS = [
    "issuer",
    "authorization_endpoint",
    "token_endpoint",
    "code_challenge_methods_supported",
    "grant_types_supported",
    "response_types_supported",
    "token_endpoint_auth_methods_supported",
    "scopes_supported",
]


@dataclass
class ProbeResult:
    url: str
    title: str
    text: str


class ProbeBlocked(httpx.RequestError):
    """A probe target outside the allowlist. Subclasses RequestError so probes report it as an observation."""


def _guard(request: httpx.Request) -> None:
    """Allow only https to hosts that resolve exclusively to public addresses.

    The model chooses probe targets and reads untrusted pages, so without this a fetched page could
    steer a probe at internal services (cloud metadata, the deployment's private network). Runs as a
    request hook, so every redirect hop is checked too. The check resolves DNS separately from the
    connection, so a DNS-rebinding host could still slip through; acceptable for unauthenticated GETs.
    """
    url = request.url
    if url.scheme != "https":
        raise ProbeBlocked(f"blocked: only https probes are allowed, got {url.scheme}://", request=request)
    try:
        infos = socket.getaddrinfo(url.host, url.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ProbeBlocked(f"blocked: cannot resolve {url.host}: {exc}", request=request) from exc
    private = sorted({info[4][0] for info in infos if not ipaddress.ip_address(info[4][0]).is_global})
    if private:
        raise ProbeBlocked(f"blocked: {url.host} resolves to non-public address {', '.join(private)}", request=request)


def make_probe_client() -> httpx.Client:
    return httpx.Client(event_hooks={"request": [_guard]})


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.chunks: list[str] = []
        self._in_title = False
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        self._in_title = tag == "title"

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip -= 1
        self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data.strip()
        elif not self._skip and data.strip():
            self.chunks.append(data.strip())


def _visible_text(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.title, " ".join(parser.chunks)[:_TEXT_LIMIT]


def probe_oauth_discovery(client: httpx.Client, host: str) -> ProbeResult:
    """Fetch the OIDC and OAuth 2.0 authorization-server metadata documents for `host`."""
    host = urlsplit(host).netloc or host
    lines: list[str] = []
    for path in ("/.well-known/openid-configuration", "/.well-known/oauth-authorization-server"):
        url = f"https://{host}{path}"
        try:
            response = client.get(url, follow_redirects=True)
        except httpx.RequestError as exc:
            lines.append(f"GET {url} -> request failed: {type(exc).__name__}: {exc}")
            continue
        lines.append(f"GET {url} -> HTTP {response.status_code}")
        if response.status_code != 200:
            continue
        try:
            document = response.json()
        except json.JSONDecodeError:
            lines.append("  body is not JSON")
            continue
        if not isinstance(document, dict):
            lines.append(f"  body is JSON but not an object ({type(document).__name__})")
            continue
        for key in _DISCOVERY_KEYS:
            if key in document:
                lines.append(f"  {key}: {json.dumps(document[key])}")
    return ProbeResult(url=f"https://{host}", title=f"OAuth discovery probe for {host}", text="\n".join(lines))


def probe_authorize_endpoint(client: httpx.Client, authorize_url: str, scope: str | None) -> ProbeResult:
    """Start an authorization request with an invalid client id and record how the provider responds.

    Some providers (Google) reject a request missing `scope` before checking the client id, so the
    agent passes a scope when it knows one to get past that first validation.
    """
    params = {
        "client_id": PROBE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": PROBE_REDIRECT_URI,
        "state": "probe",
    }
    if scope is not None:
        params["scope"] = scope
    url = f"{authorize_url}{'&' if '?' in authorize_url else '?'}{urlencode(params)}"
    try:
        response = client.get(url, follow_redirects=True)
    except httpx.RequestError as exc:
        return ProbeResult(url=authorize_url, title="Authorize endpoint probe", text=f"request failed: {type(exc).__name__}: {exc}")

    lines = [f"GET {url}"]
    for hop in response.history:
        lines.append(f"  HTTP {hop.status_code} -> {hop.headers.get('location')}")
    lines.append(f"  final: HTTP {response.status_code} at {response.url}")
    title, text = _visible_text(response.text)
    lines.append(f"  page title: {title!r}")
    lines.append(f"  visible text: {text}")
    return ProbeResult(url=authorize_url, title="Authorize endpoint probe", text="\n".join(lines))
