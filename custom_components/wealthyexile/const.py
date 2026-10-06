"""Constants for the WealthyExile integration."""
from datetime import timedelta

DOMAIN = "wealthyexile"

CONF_SESSION_COOKIE_NAME = "session_cookie_name"
CONF_SESSION_COOKIE_VALUE = "session_cookie_value"

STASH_URL = "https://wealthyexile.com/stash?primary=true"

UPDATE_INTERVAL = timedelta(minutes=5)

ISSUE_PARSE_FAILED = "stash_parse_failed"

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
