"""Config flow for Kryptex Pool."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KryptexAPIError, KryptexClient
from .const import CONF_ADDRESS, CONF_COIN, DOMAIN


class KryptexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Kryptex Pool configuration flow."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            coin = str(user_input[CONF_COIN]).strip().upper()
            address = str(user_input[CONF_ADDRESS]).strip()
            client = KryptexClient(async_get_clientsession(self.hass), coin, address)
            try:
                await client.async_validate()
            except KryptexAPIError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{coin.lower()}_{address.lower()}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Kryptex {coin}",
                    data={CONF_COIN: coin, CONF_ADDRESS: address},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_COIN): str,
                vol.Required(CONF_ADDRESS): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
