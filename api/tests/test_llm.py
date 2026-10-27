import anthropic
import httpx2
import pytest

from oauth_guides_api.llm import is_transient


def _error(cls, status: int, error_type: str):
    response = httpx2.Response(status, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    return cls("x", response=response, body={"type": "error", "error": {"type": error_type, "message": "x"}})


@pytest.mark.parametrize(
    ("cls", "status", "error_type", "expected"),
    [
        (anthropic.OverloadedError, 529, "overloaded_error", True),
        (anthropic.RateLimitError, 429, "rate_limit_error", True),
        # Mid-stream errors arrive after HTTP 200 and are raised as the base class.
        (anthropic.APIStatusError, 200, "overloaded_error", True),
        (anthropic.APIStatusError, 200, "api_error", True),
        (anthropic.BadRequestError, 400, "invalid_request_error", False),
        (anthropic.AuthenticationError, 401, "authentication_error", False),
        (anthropic.APIStatusError, 400, "billing_error", False),
    ],
)
def test_only_transient_failures_fall_back(cls, status, error_type, expected):
    assert is_transient(_error(cls, status, error_type)) is expected
