"""Constants for the WealthyExile integration."""
from datetime import timedelta

DOMAIN = "wealthyexile"

CONF_CODE_VERIFIER_NAME = "code_verifier_name"
CONF_CODE_VERIFIER_VALUE = "code_verifier_value"
CONF_SESSION_COOKIE_NAME = "session_cookie_name"
CONF_SESSION_COOKIE_VALUE = "session_cookie_value"

# The code_verifier cookie's *name* looked stable across accounts/leagues
# in testing -- unlike the session cookie's name, which embeds the current
# PoE league (e.g. "session-Allflame-1") and changes every league. Used as
# the config flow's default for that field, not hardcoded/assumed elsewhere.
DEFAULT_CODE_VERIFIER_NAME = "code_verifier"

STASH_URL = "https://wealthyexile.com/stash?primary=true"

UPDATE_INTERVAL = timedelta(minutes=5)

ISSUE_PARSE_FAILED = "stash_parse_failed"

# --- WealthyExile deployment-specific values --------------------------------
#
# These three values are tied to WealthyExile's *current* Next.js build.
# WealthyExile is an actively developed SaaS; whenever they redeploy, these
# go stale and every poll fails (you'll see a "WealthyExile-Antwort konnte
# nicht gelesen werden" repair issue show up under Settings > Repairs).
#
# To refresh them:
#   1. Open https://wealthyexile.com/stash while logged in, open your
#      browser's DevTools -> Network tab.
#   2. Trigger a stash sync (e.g. reload the page).
#   3. Find the POST request to "stash?primary=true".
#   4. Copy its "next-action" request header into NEXT_ACTION_HASH below.
#   5. Copy its "x-deployment-id" request header into X_DEPLOYMENT_ID below.
#   6. "next-router-state-tree" just encodes the /stash route and rarely
#      changes, but copy it too if requests keep failing after steps 4-5.
#   7. Restart Home Assistant (or reload the integration).
NEXT_ACTION_HASH = "7001717f091484e5b76feb4ef197a249d1d369972c"
X_DEPLOYMENT_ID = "dpl_22PkR8Zu39L1ZHkMjg1hdpgE7tPP"
NEXT_ROUTER_STATE_TREE = (
    "%5B%22%22%2C%7B%22children%22%3A%5B%22(routes)%22%2C%7B%22children%22"
    "%3A%5B%22stash%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C"
    "null%2Cnull%2C4096%5D%7D%2Cnull%2Cnull%2C4096%5D%7D%2Cnull%2Cnull%2C4096"
    "%5D%7D%2Cnull%2Cnull%2C4176%5D"
)

# --- Stash tab type icons ----------------------------------------------------
#
# The stash payload doesn't include an icon URL per tab -- WealthyExile's own
# frontend maps each tab `type` to one of these GGG CDN icons client-side.
# Pulled from a real browser session's network capture (signed `key` query
# param and all); these looked like stable, generic per-type assets rather
# than anything account-specific, but that's unconfirmed, and this only
# covers the tab types actually seen on one real account -- an unmapped type
# (e.g. a tab kind that account didn't have) just gets no icon, not an error.
TAB_TYPE_ICON_URLS: dict[str, str] = {
    "CurrencyStash": "https://web.poecdn.com/protected/image/layout/stash/currency-tab-icon.png?v=1680235310710&key=c4JmwvlEdlm1iitgRJ-LtQ",
    "FragmentStash": "https://web.poecdn.com/protected/image/layout/stash/fragment-tab-icon.png?v=1680235310830&key=NIXjytgKBeGX-0ed5uJWeA",
    "MapStash": "https://web.poecdn.com/protected/image/layout/stash/map-tab-icon.png?v=1680235310894&key=jLp8L5BgKpzzyf8Jdu51Zg",
    "GemStash": "https://web.poecdn.com/protected/image/layout/stash/gem-tab-icon.png?v=1680235310878&key=KE0pPt-_F4uZcdNWL6ff4Q",
    "EssenceStash": "https://web.poecdn.com/protected/image/layout/stash/essence-tab-icon.png?v=1680235310746&key=3sC1L24_-V0QEze0P8r_Dg",
    "UltimatumStash": "https://web.poecdn.com/protected/image/layout/stash/ultimatum-tab-icon.png?v=1701820752236&key=FX2cpC4HmHxbMS3bQvXi-A",
    "BlightStash": "https://web.poecdn.com/protected/image/layout/stash/blight-tab-icon.png?v=1680235310698&key=PL1k11by4nAQDMPTAnPZdA",
    "DeliriumStash": "https://web.poecdn.com/protected/image/layout/stash/delirium-tab-icon.png?v=1680235310730&key=sIX1JMexEbOTIezUWYJqvg",
    "DivinationCardStash": "https://web.poecdn.com/protected/image/layout/stash/divination-tab-icon.png?v=1680235310746&key=FaLsxYtmuqBXkJebdF62_w",
    "DelveStash": "https://web.poecdn.com/protected/image/layout/stash/delve-tab-icon.png?v=1680235310746&key=1eC3WO6hAEtNVN7wtLT6jA",
}
