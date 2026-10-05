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
