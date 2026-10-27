from oauth_guides_api.agent import Investigation


def _investigation() -> tuple[Investigation, list[dict]]:
    events: list[dict] = []
    # Malformed calls are answered before any LLM, Composio, or HTTP use, so none are needed here.
    return Investigation(llm=None, composio=None, http=None, emit=events.append), events


def test_missing_argument_is_returned_to_the_model_not_raised():
    inv, events = _investigation()
    content, is_error = inv._run_tool("probe_authorize_endpoint", {"scope": "repo"})
    assert is_error
    assert content == "probe_authorize_endpoint is missing required argument(s): authorize_url."
    assert events[-1]["type"] == "tool"


def test_unknown_tool_is_returned_to_the_model_not_raised():
    inv, _ = _investigation()
    content, is_error = inv._run_tool("delete_everything", {})
    assert is_error
    assert content.startswith("Unknown tool 'delete_everything'. Available: probe_oauth_discovery")
    assert "finish_guide" in content
