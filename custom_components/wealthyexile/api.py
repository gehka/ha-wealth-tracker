"""HTTP client for WealthyExile's `/stash` page.

Does a single, plain authenticated GET of the page and reads back whatever
stash state WealthyExile currently has -- it never triggers a new sync.
Triggering a sync is a mutating action (it validates against and updates
WealthyExile's own server-side state) and is deliberately left to the
user: either by clicking "Sync" on wealthyexile.com themselves, or via
whatever WealthyExile's own game-session sync behavior is. This client
only ever reads, which sidesteps a whole class of problems a prior version
of this integration had to work around: the sync-trigger endpoint's
`lastSynced`/`lastHourlySync` concurrency check racing against the user's
own browser, and the hardcoded `next-action`/`x-deployment-id` values
(needed only for that POST, not for this GET) going stale on every
WealthyExile redeploy. It also means polling on a schedule never hammers
WealthyExile with sync requests nobody asked for.

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

from .const import STASH_URL
from .parser import extract_stash_payload_from_html

_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Headers beyond Accept/Cookie that matched a real browser request during
# testing. Unclear which of these actually matter to WealthyExile/Vercel
# vs. are just cargo-culted from the capture, but there's no reason to
# find out the hard way by stripping them.
_BROWSER_LIKE_HEADERS = {
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.6",
    "sec-ch-ua": '"Brave";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "sec-gpc": "1",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
    ),
}


class WealthyExileApiClient:
    """Reads the current stash state from WealthyExile.

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
        """Return the parsed `{"user": ..., "priceMap": ...}` currently on
        WealthyExile. Opens its own aiohttp session per call rather than
        reusing Home Assistant's shared one -- see module docstring for why.
        """
        headers = {**_BROWSER_LIKE_HEADERS, "cookie": self._cookie}
        async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar()) as session:
            async with session.get(STASH_URL, headers=headers, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                html = await resp.text()

        return extract_stash_payload_from_html(html)
