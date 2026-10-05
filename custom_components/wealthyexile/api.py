"""HTTP client for WealthyExile's `/stash` page and Server Action endpoint.

Every call does two requests:

1. A plain authenticated GET of the `/stash` page, to learn the account's
   *current* `lastSynced`/`lastHourlySync` straight from the server (see
   `parser.extract_stash_payload_from_html` for why this works where a
   Server Action call alone doesn't).
2. A POST invoking the sync-trigger Server Action with those exact values,
   which WealthyExile validates against what it has stored for the account
   and rejects (`WealthyExileParseError`) if they don't match -- e.g. if
   something else (the user's own browser) synced in between our GET and
   POST. That's a real but narrow race window (milliseconds in practice),
   not an ongoing state-tracking requirement -- this client holds no
   cross-call state at all, which is deliberate: every call re-learns the
   current state from scratch, so nothing can "lose the thread" between
   polls, HA restarts, etc.

Deliberately does *not* use Home Assistant's shared aiohttp session
(`async_get_clientsession`): that session keeps a real cookie jar, and in
testing, requests made through it got silently redirected to PoE's OAuth
login -- i.e. treated as unauthenticated -- with the *exact* cookie value
that worked fine via a bare client (confirmed from the HA host itself,
via curl, ruling out a network/IP difference). Likely cause: the shared
session's cookie jar merging with our explicit `Cookie` header in some
way the server doesn't like. Using a private session with a dummy cookie
jar sidesteps the question entirely -- only the header we set is ever
sent.
"""
from __future__ import annotations

from typing import Any

import aiohttp

from .const import (
    NEXT_ACTION_HASH,
    NEXT_ROUTER_STATE_TREE,
    STASH_URL,
    X_DEPLOYMENT_ID,
)
from .parser import extract_stash_payload, extract_stash_payload_from_html

_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Headers beyond Accept/Cookie/Content-Type that matched a real browser
# request during testing. Unclear which of these actually matter to
# WealthyExile/Vercel vs. are just cargo-culted from the capture, but
# there's no reason to find out the hard way by stripping them.
_BROWSER_LIKE_HEADERS = {
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.6",
    "sec-ch-ua": '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-gpc": "1",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
    ),
}


class WealthyExileApiClient:
    """Fetches a fresh stash sync from WealthyExile.

    Takes the two cookies as separate name/value pairs (not one opaque
    header string) because the session cookie's *name* embeds the current
    PoE league (e.g. `session-Allflame-1`) and changes every league --
    asking for name+value separately makes that obvious to whoever is
    filling in the config flow, instead of silently breaking three months
    later with no clue why.
    """

    def __init__(
        self,
        code_verifier_name: str,
        code_verifier_value: str,
        session_cookie_name: str,
        session_cookie_value: str,
    ) -> None:
        self._cookie = (
            f"{code_verifier_name}={code_verifier_value}; "
            f"{session_cookie_name}={session_cookie_value}"
        )

    async def async_fetch_stash(self) -> dict[str, Any]:
        """GET current state, then POST a sync trigger using it. Returns the
        parsed `{"user": ..., "priceMap": ...}` from the sync response.

        Opens its own aiohttp session per call rather than reusing Home
        Assistant's shared one -- see module docstring for why.
        """
        async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar()) as session:
            user = (await self._async_get_current_state(session))["user"]
            last_synced = user["lastSynced"]
            last_hourly = user["lastHourlySync"]

            return await self._async_trigger_sync(session, last_synced, last_hourly)

    async def _async_get_current_state(
        self, session: aiohttp.ClientSession
    ) -> dict[str, Any]:
        headers = {
            **_BROWSER_LIKE_HEADERS,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "cookie": self._cookie,
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        }
        async with session.get(STASH_URL, headers=headers, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            html = await resp.text()

        return extract_stash_payload_from_html(html)

    async def _async_trigger_sync(
        self, session: aiohttp.ClientSession, last_synced: str, last_hourly: str
    ) -> dict[str, Any]:
        body = f'[1,"{last_synced}","{last_hourly}"]'
        headers = {
            **_BROWSER_LIKE_HEADERS,
            "accept": "text/x-component",
            "content-type": "text/plain;charset=UTF-8",
            "cookie": self._cookie,
            "next-action": NEXT_ACTION_HASH,
            "next-router-state-tree": NEXT_ROUTER_STATE_TREE,
            "origin": "https://wealthyexile.com",
            "priority": "u=1, i",
            "referer": "https://wealthyexile.com/stash",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-deployment-id": X_DEPLOYMENT_ID,
        }
        async with session.post(
            STASH_URL, headers=headers, data=body, timeout=_TIMEOUT
        ) as resp:
            resp.raise_for_status()
            raw_text = await resp.text()

        return extract_stash_payload(raw_text)
