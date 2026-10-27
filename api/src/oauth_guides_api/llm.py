"""Claude via the Anthropic API, falling back to OpenRouter.

OpenRouter exposes an Anthropic-compatible Messages endpoint, so both clients are the Anthropic
SDK and the tool-use format is identical; only base URL and credential differ.
"""

import os
from typing import Literal

import anthropic
from anthropic.types import Message
from anthropic.types.beta import BetaMessage

MODEL = "claude-sonnet-5-5"
# A free model, at the user's request (the OpenRouter account has no credits). Picked from the
# `:free` models listing `tools` support at https://openrouter.ai/api/v1/models; it completed a
# tool call in ~3s through the Anthropic-compatible endpoint on 2026-10-28, where
# nemotron-3-ultra-550b-a55b:free hit OpenRouter's upstream idle timeout on a long turn. It is not
# Claude, so guide quality differs from the primary path; provenance records the model per guide.
OPENROUTER_MODEL = "nvidia/nemotron-3.5-super-vl:free"
# The SDK appends /v1/messages itself (OpenRouter Claude Code integration docs).
OPENROUTER_BASE_URL = "https://openrouter.ai/api"
# Server-side refusal fallback: on a safety decline the API re-runs the turn on a model chosen by
# refusal category. Claude API only, so it is not sent through OpenRouter.
REFUSAL_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Transient provider-side failures only. Auth, permission and bad-request errors are our bugs
# and must surface instead of being masked by a second provider.
_FALLBACK_ON = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.ServiceUnavailableError,
    anthropic.OverloadedError,
)

Provider = Literal["anthropic", "openrouter"]


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"environment variable {name} is not set")
    return value


class LLM:
    def __init__(self) -> None:
        # Without GUIDES_ANTHROPIC_API_KEY every turn goes through OpenRouter. A key that is set but
        # rejected still raises, so a bad key is never masked by the fallback. Prefixed because a
        # shell-wide ANTHROPIC_API_KEY would otherwise take precedence over api/.env.
        key = os.environ.get("GUIDES_ANTHROPIC_API_KEY")
        self._primary = anthropic.Anthropic(api_key=key) if key else None
        self._fallback = anthropic.Anthropic(base_url=OPENROUTER_BASE_URL, auth_token=require_env("OPENROUTER_API_KEY"))

    def create(self, **kwargs) -> tuple[Message | BetaMessage, Provider]:
        """One streamed turn. Streaming because large max_tokens is refused on non-streaming calls."""
        if self._primary is None:
            return self._openrouter(**kwargs)
        try:
            with self._primary.beta.messages.stream(
                model=MODEL, betas=[REFUSAL_FALLBACK_BETA], fallbacks="default", **kwargs
            ) as stream:
                return stream.get_final_message(), "anthropic"
        except _FALLBACK_ON:
            return self._openrouter(**kwargs)

    def _openrouter(self, **kwargs) -> tuple[Message, Provider]:
        with self._fallback.messages.stream(model=OPENROUTER_MODEL, **kwargs) as stream:
            return stream.get_final_message(), "openrouter"
