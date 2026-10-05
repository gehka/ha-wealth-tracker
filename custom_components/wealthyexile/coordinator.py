"""DataUpdateCoordinator for the WealthyExile integration."""
from __future__ import annotations

import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WealthyExileApiClient
from .calculations import DerivedData, compute_derived
from .const import (
    CONF_CODE_VERIFIER_NAME,
    CONF_CODE_VERIFIER_VALUE,
    CONF_SESSION_COOKIE_NAME,
    CONF_SESSION_COOKIE_VALUE,
    DOMAIN,
    ISSUE_PARSE_FAILED,
    UPDATE_INTERVAL,
)
from .parser import WealthyExileParseError

_LOGGER = logging.getLogger(__name__)

# A single WealthyExileParseError is usually just the GET->POST race: our
# GET learned the current lastSynced, but something else (the user's own
# browser) synced before our POST landed, so the values we sent are
# already stale. That's expected occasionally and self-heals on the next
# poll -- only surface a repair issue if it keeps happening, which more
# likely means a real redeploy broke NEXT_ACTION_HASH/X_DEPLOYMENT_ID.
_CONSECUTIVE_FAILURES_BEFORE_REPAIR_ISSUE = 3


class WealthyExileCoordinator(DataUpdateCoordinator[DerivedData]):
    """Polls WealthyExile every UPDATE_INTERVAL and exposes derived data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self._client = WealthyExileApiClient(
            entry.data[CONF_CODE_VERIFIER_NAME],
            entry.data[CONF_CODE_VERIFIER_VALUE],
            entry.data[CONF_SESSION_COOKIE_NAME],
            entry.data[CONF_SESSION_COOKIE_VALUE],
        )
        # Baseline for the "session gain" sensor: the total value at the
        # first successful poll after HA (re)started. Not a true gaming
        # "session" boundary, just a practical proxy for one.
        self._session_baseline_divine: float | None = None
        self._consecutive_parse_failures = 0

    async def _async_update_data(self) -> DerivedData:
        try:
            payload = await self._client.async_fetch_stash()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error talking to WealthyExile: {err}") from err
        except WealthyExileParseError as err:
            self._consecutive_parse_failures += 1
            if self._consecutive_parse_failures >= _CONSECUTIVE_FAILURES_BEFORE_REPAIR_ISSUE:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    ISSUE_PARSE_FAILED,
                    is_fixable=False,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key=ISSUE_PARSE_FAILED,
                )
            raise UpdateFailed(str(err)) from err

        self._consecutive_parse_failures = 0
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_PARSE_FAILED)

        derived = compute_derived(payload)

        if self._session_baseline_divine is None:
            self._session_baseline_divine = derived.total_value_divine
        derived.session_gain_divine = derived.total_value_divine - self._session_baseline_divine

        return derived
