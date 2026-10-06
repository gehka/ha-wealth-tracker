from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "wealthyexile"))

from parser import (  # noqa: E402
    WealthyExileParseError,
    extract_stash_payload,
    extract_stash_payload_from_html,
)

FIXTURE = Path(__file__).parent / "fixtures" / "stash_response.txt"
HTML_FIXTURE = Path(__file__).parent / "fixtures" / "stash_page.html"


def test_extract_stash_payload_from_fixture():
    raw_text = FIXTURE.read_text()
    payload = extract_stash_payload(raw_text)

    assert payload["user"]["preferredLeague"] == "Allflame"
    assert len(payload["user"]["tabs"]) == 2
    assert payload["priceMap"][0]["name"] == "Divine Orb"


def test_extract_stash_payload_ignores_surrounding_chunks():
    raw_text = FIXTURE.read_text()
    payload = extract_stash_payload(raw_text)
    # Sanity: the marker appears once, nested arrays/objects around it parsed cleanly.
    assert payload["user"]["tabs"][0]["name"] == "$$"
    assert payload["user"]["tabs"][1]["items"][0]["price"]["name"] == "Valdo's Puzzle Box"


def test_extract_stash_payload_missing_marker_raises():
    with pytest.raises(WealthyExileParseError):
        extract_stash_payload("not a flight response at all")


def test_extract_stash_payload_surfaces_server_error():
    raw_text = (
        '0:{"a":"$@1","f":"","q":"?primary=true","i":false}\n'
        '1:{"error":"Hourly sync just happened 2 years ago."}\n'
    )
    with pytest.raises(WealthyExileParseError, match="Hourly sync just happened"):
        extract_stash_payload(raw_text)


def test_extract_stash_payload_truncated_raises():
    raw_text = FIXTURE.read_text()
    start = raw_text.find('{"user":{"preferredLeague"')
    truncated = raw_text[: start + 50]
    with pytest.raises(WealthyExileParseError):
        extract_stash_payload(truncated)


def test_extract_stash_payload_from_html_fixture():
    html = HTML_FIXTURE.read_text()
    payload = extract_stash_payload_from_html(html)

    assert payload["user"]["preferredLeague"] == "Allflame"
    assert payload["user"]["lastSynced"] == "$D2026-10-05T16:59:08.000Z"
    assert payload["priceMap"][0]["name"] == "Divine Orb"


def test_extract_stash_payload_from_html_ignores_decoy_chunks():
    html = HTML_FIXTURE.read_text()
    payload = extract_stash_payload_from_html(html)
    # Sanity: unescaping didn't mangle nested quotes/braces in item data.
    assert payload["user"]["tabs"][0]["items"][0]["price"]["name"] == "Divine Orb"


def test_extract_stash_payload_from_html_missing_chunks_raises():
    with pytest.raises(WealthyExileParseError):
        extract_stash_payload_from_html("<html><body>no hydration data here</body></html>")
