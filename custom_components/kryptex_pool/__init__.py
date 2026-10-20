"""Kryptex Pool integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KryptexAPIError, KryptexClient
from .const import CONF_ADDRESS, CONF_COIN, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
type KryptexConfigEntry = ConfigEntry[DataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: KryptexConfigEntry) -> bool:
    """Set up Kryptex Pool from a config entry."""
    client = KryptexClient(
        async_get_clientsession(hass),
        entry.data[CONF_COIN],
        entry.data[CONF_ADDRESS],
    )

    async def async_update_data():
        try:
            return await client.async_get_data()
        except KryptexAPIError as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KryptexConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
