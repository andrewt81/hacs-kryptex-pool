"""Kryptex Pool integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KryptexAPIError, KryptexClient
from .const import (
    CONF_ADDRESS,
    CONF_COIN,
    DOMAIN,
    SCAN_INTERVAL,
    is_kryptex_account,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
type KryptexConfigEntry = ConfigEntry[DataUpdateCoordinator]

BALANCE_SENSOR_KEYS = ("confirmed", "unconfirmed", "total", "paid")


async def async_migrate_entry(
    hass: HomeAssistant, entry: KryptexConfigEntry
) -> bool:
    """Migrate existing entries to disable inaccessible account balances."""
    if entry.version < 2:
        coin = str(entry.data[CONF_COIN])
        address = str(entry.data[CONF_ADDRESS])
        if is_kryptex_account(address):
            registry = er.async_get(hass)
            device_id = f"{coin.lower()}_{address.lower()}"
            for key in BALANCE_SENSOR_KEYS:
                entity_id = registry.async_get_entity_id(
                    "sensor", DOMAIN, f"{device_id}_{key}"
                )
                if entity_id is None:
                    continue
                registry_entry = registry.async_get(entity_id)
                if registry_entry and registry_entry.disabled_by is None:
                    registry.async_update_entity(
                        entity_id,
                        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                    )
        hass.config_entries.async_update_entry(entry, version=2)
    return True


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
