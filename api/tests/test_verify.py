from conftest import claim, draft, source, step

from oauth_guides_api.verify import verify

PAGE = source("s1", "page", "Apps requesting restricted scopes must complete a security assessment\nby an approved assessor.")
SEARCH = source("s2", "search", "Apps requesting restricted scopes must complete a security assessment by an approved assessor.")
PROBE = source("s3", "probe", "Error 401: invalid_client The OAuth client was not found.")


def _single(c, sources):
    checked, downgrades = verify(draft(requirements=[c]), sources)
    return checked.requirements[0].status, [d.reason for d in downgrades]


def test_sourced_claim_with_quote_in_cited_page_is_kept_despite_whitespace_and_case():
    status, reasons = _single(claim("sourced", ["s1"], "restricted scopes must complete a SECURITY assessment by an approved"), [PAGE])
    assert (status, reasons) == ("sourced", [])


def test_sourced_claim_whose_quote_is_not_in_the_page_is_downgraded():
    status, reasons = _single(claim("sourced", ["s1"], "no security assessment is ever required"), [PAGE])
    assert (status, reasons) == ("inferred", ["quote not found in any cited fetched page"])


def test_search_snippet_alone_does_not_support_a_sourced_claim():
    status, reasons = _single(claim("sourced", ["s2"], "restricted scopes must complete a security assessment"), [SEARCH])
    assert (status, reasons) == ("inferred", ["quote not found in any cited fetched page"])


def test_short_quote_does_not_count_as_support():
    status, reasons = _single(claim("sourced", ["s1"], "restricted"), [PAGE])
    assert (status, reasons) == ("inferred", ["marked sourced without a quote of at least 20 characters"])


def test_tested_claim_requires_a_probe_source():
    assert _single(claim("tested", ["s3"]), [PAGE, PROBE]) == ("tested", [])
    assert _single(claim("tested", ["s1"]), [PAGE, PROBE]) == ("inferred", ["marked tested but cites no probe result"])


def test_unknown_source_id_is_downgraded():
    assert _single(claim("sourced", ["s9"], "restricted scopes must complete"), [PAGE]) == ("inferred", ["cites unknown source ids ['s9']"])


def test_unknown_and_inferred_claims_are_never_changed_or_counted():
    assert _single(claim("unknown", ["s9"]), [PAGE]) == ("unknown", [])
    assert _single(claim("inferred", ["s9"]), [PAGE]) == ("inferred", [])


def test_claims_inside_steps_are_checked_and_original_draft_is_untouched():
    original = draft(steps=[step(claims=[claim("tested", ["s1"])])])
    checked, downgrades = verify(original, [PAGE])
    assert checked.steps[0].claims[0].status == "inferred"
    assert original.steps[0].claims[0].status == "tested"
    assert downgrades[0].location == "steps[0] dev step"
