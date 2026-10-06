"""Parsing helpers for WealthyExile's `/stash` page.

The page is a Next.js app: a plain GET of `/stash?primary=true` returns
full HTML, but the actual stash data isn't in regular markup -- it's
embedded as a JSON-string-escaped React Server Components "Flight" payload
inside `<script>self.__next_f.push([N,"..."])</script>` hydration tags.
The data we need is somewhere in one of those chunks, but *not* at a fixed
chunk index -- that index is an internal React component id that can
shift between WealthyExile deployments. So instead of parsing by position,
we locate the payload by its distinctive content and extract it with
brace-matching.
"""
from __future__ import annotations

import json
from typing import Any

_USER_MARKER = '{"user":{"preferredLeague"'
_ERROR_MARKER = '{"error":"'
_NEXT_F_PUSH_MARKER = "self.__next_f.push(["


class WealthyExileParseError(Exception):
    """Raised when the stash payload can't be located or parsed.

    Most likely cause: WealthyExile redeployed and changed their page
    structure, or the session cookie is no longer valid.
    """


def extract_stash_payload(raw_text: str) -> dict[str, Any]:
    """Extract and parse the `{"user": ..., "priceMap": ...}` object."""
    start = raw_text.find(_USER_MARKER)
    if start == -1:
        error_message = _extract_server_error(raw_text)
        if error_message is not None:
            raise WealthyExileParseError(f"WealthyExile returned an error: {error_message}")
        raise WealthyExileParseError(
            "Could not find the stash data marker in the response. "
            "WealthyExile may have redeployed and changed their response "
            "format, or the session cookie is no longer valid."
        )

    end = _find_matching_brace(raw_text, start)
    if end is None:
        raise WealthyExileParseError(
            "Found the stash data marker but couldn't find its closing "
            "brace (response may have been truncated)."
        )

    payload_text = raw_text[start : end + 1]
    try:
        payload: dict[str, Any] = json.loads(payload_text)
    except json.JSONDecodeError as err:
        raise WealthyExileParseError(f"Stash data wasn't valid JSON: {err}") from err

    if "user" not in payload:
        raise WealthyExileParseError("Parsed payload is missing the 'user' key.")

    return payload


def extract_stash_payload_from_html(html_text: str) -> dict[str, Any]:
    """Extract the stash payload from a plain GET of /stash (full HTML page).

    Next.js embeds the page's React Flight data inside
    `<script>self.__next_f.push([N,"..."])</script>` tags for hydration,
    but as a JSON-string-escaped literal (every `"` becomes `\\"`). We
    can't brace-match that directly -- each push() call's second argument
    is first unescaped as a JSON string (which turns it back into plain
    Flight-stream text), and *that* is handed to `extract_stash_payload`.
    """
    pos = 0
    while True:
        start = html_text.find(_NEXT_F_PUSH_MARKER, pos)
        if start == -1:
            raise WealthyExileParseError(
                "No self.__next_f.push(...) hydration chunks found in the "
                "HTML. WealthyExile may have redeployed and changed their "
                "page structure, or the session cookie is no longer valid."
            )

        quote_start = html_text.find('"', start)
        if quote_start == -1:
            pos = start + len(_NEXT_F_PUSH_MARKER)
            continue

        end = _find_matching_quote(html_text, quote_start)
        if end is None:
            pos = quote_start + 1
            continue

        raw_escaped = html_text[quote_start : end + 1]
        try:
            unescaped = json.loads(raw_escaped)
        except json.JSONDecodeError:
            pos = end + 1
            continue

        if _USER_MARKER in unescaped:
            return extract_stash_payload(unescaped)
        pos = end + 1


def _find_matching_quote(text: str, open_quote_index: int) -> int | None:
    """Return the index of the unescaped closing quote for a JSON string
    literal that starts at `open_quote_index`."""
    escaped = False
    for i in range(open_quote_index + 1, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == '"':
            return i
    return None


def _extract_server_error(raw_text: str) -> str | None:
    """Pull a `{"error": "..."}` message out of the response, if present.

    Defensive fallback for when WealthyExile returns a 200 OK with an
    error payload instead of the expected page content -- surfaces
    whatever message they included directly, instead of a generic
    "couldn't find the data" error.
    """
    start = raw_text.find(_ERROR_MARKER)
    if start == -1:
        return None
    end = _find_matching_brace(raw_text, start)
    if end is None:
        return None
    try:
        parsed = json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed.get("error")


def _find_matching_brace(text: str, open_brace_index: int) -> int | None:
    """Return the index of the closing brace matching the opening one.

    Tracks string state so braces inside JSON string values don't throw
    off the depth count.
    """
    depth = 0
    in_string = False
    escape = False
    for i in range(open_brace_index, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return None
