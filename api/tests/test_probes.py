"""The probe allowlist. Blocked targets never leave this machine; IP literals resolve without DNS."""

import pytest

from oauth_guides_api.probes import make_probe_client, probe_authorize_endpoint, probe_oauth_discovery


@pytest.mark.parametrize(
    ("target", "reason"),
    [
        ("http://example.com/authorize", "only https probes are allowed"),
        ("https://127.0.0.1/authorize", "non-public address 127.0.0.1"),
        ("https://169.254.169.254/latest/meta-data", "non-public address 169.254.169.254"),
        ("https://10.0.0.5/authorize", "non-public address 10.0.0.5"),
        ("https://[::1]/authorize", "non-public address ::1"),
        ("https://localhost/authorize", "non-public address"),
    ],
)
def test_authorize_probe_refuses_non_public_targets(target, reason):
    with make_probe_client() as client:
        result = probe_authorize_endpoint(client, target, None)
    assert "request failed: ProbeBlocked: blocked:" in result.text
    assert reason in result.text


def test_discovery_probe_refuses_internal_host():
    with make_probe_client() as client:
        result = probe_oauth_discovery(client, "169.254.169.254")
    assert result.text.count("ProbeBlocked") == 2
