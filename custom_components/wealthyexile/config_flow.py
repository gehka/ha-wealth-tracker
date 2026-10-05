"""Config flow for the WealthyExile integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries

from .api import WealthyExileApiClient
from .const import (
    CONF_CODE_VERIFIER_NAME,
    CONF_CODE_VERIFIER_VALUE,
    CONF_SESSION_COOKIE_NAME,
    CONF_SESSION_COOKIE_VALUE,
    DEFAULT_CODE_VERIFIER_NAME,
    DOMAIN,
)
from .parser import WealthyExileParseError

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CODE_VERIFIER_NAME, default=DEFAULT_CODE_VERIFIER_NAME): str,
        vol.Required(CONF_CODE_VERIFIER_VALUE): str,
        vol.Required(CONF_SESSION_COOKIE_NAME): str,
        vol.Required(CONF_SESSION_COOKIE_VALUE): str,
    }
)


class WealthyExileConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WealthyExile."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            code_verifier_name = user_input[CONF_CODE_VERIFIER_NAME].strip()
            code_verifier_value = user_input[CONF_CODE_VERIFIER_VALUE].strip()
            session_cookie_name = user_input[CONF_SESSION_COOKIE_NAME].strip()
            session_cookie_value = user_input[CONF_SESSION_COOKIE_VALUE].strip()

            client = WealthyExileApiClient(
                code_verifier_name,
                code_verifier_value,
                session_cookie_name,
                session_cookie_value,
            )

            try:
                payload = await client.async_fetch_stash()
            except aiohttp.ClientError:
                _LOGGER.exception("Could not reach WealthyExile during setup")
                errors["base"] = "cannot_connect"
            except WealthyExileParseError:
                _LOGGER.exception("Could not parse WealthyExile's response during setup")
                errors["base"] = "parse_failed"
            else:
                user = payload["user"]
                league = user["preferredLeague"]
                tabs = user.get("tabs") or []
                account_name = tabs[0]["username"] if tabs else league

                await self.async_set_unique_id(account_name)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"WealthyExile ({league})",
                    data={
                        CONF_CODE_VERIFIER_NAME: code_verifier_name,
                        CONF_CODE_VERIFIER_VALUE: code_verifier_value,
                        CONF_SESSION_COOKIE_NAME: session_cookie_name,
                        CONF_SESSION_COOKIE_VALUE: session_cookie_value,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
