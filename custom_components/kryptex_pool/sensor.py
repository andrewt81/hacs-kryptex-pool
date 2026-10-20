"""Sensors for Kryptex Pool."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .api import numeric_value, worker_hashrate, worker_is_online
from .const import CONF_ADDRESS, CONF_COIN, DOMAIN


@dataclass(frozen=True, kw_only=True)
class KryptexSensorDescription(SensorEntityDescription):
    """Describe a Kryptex sensor."""

    value_fn: Callable[[dict[str, Any]], int | float]
    coin_unit: bool = False


SENSORS = (
    KryptexSensorDescription(
        key="confirmed",
        translation_key="confirmed",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL,
        coin_unit=True,
        value_fn=lambda data: numeric_value(data["balance"], "confirmed"),
    ),
    KryptexSensorDescription(
        key="unconfirmed",
        translation_key="unconfirmed",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL,
        coin_unit=True,
        value_fn=lambda data: numeric_value(data["balance"], "unconfirmed"),
    ),
    KryptexSensorDescription(
        key="total",
        translation_key="total",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL,
        coin_unit=True,
        value_fn=lambda data: numeric_value(data["balance"], "total"),
    ),
    KryptexSensorDescription(
        key="paid",
        translation_key="paid",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL_INCREASING,
        coin_unit=True,
        value_fn=lambda data: numeric_value(
            data["balance"], "miner.paidBalance", "paid", "paidBalance"
        ),
    ),
    KryptexSensorDescription(
        key="workers",
        translation_key="workers",
        value_fn=lambda data: len(data["workers"]),
    ),
    KryptexSensorDescription(
        key="online_workers",
        translation_key="online_workers",
        value_fn=lambda data: sum(
            worker_is_online(worker) for worker in data["workers"]
        ),
    ),
    KryptexSensorDescription(
        key="hashrate",
        translation_key="hashrate",
        native_unit_of_measurement="H/s",
        suggested_display_precision=2,
        value_fn=lambda data: round(
            sum(worker_hashrate(worker) for worker in data["workers"]), 2
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Kryptex sensors."""
    coordinator = entry.runtime_data
    async_add_entities(KryptexSensor(coordinator, entry, item) for item in SENSORS)


class KryptexSensor(CoordinatorEntity[DataUpdateCoordinator], SensorEntity):
    """A sensor backed by the shared Kryptex coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: KryptexSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        coin = entry.data[CONF_COIN]
        address = entry.data[CONF_ADDRESS]
        device_id = f"{coin.lower()}_{address.lower()}"
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": f"Kryptex {coin}",
            "manufacturer": "Kryptex",
            "model": "Mining Pool",
        }
        if description.coin_unit:
            self._attr_native_unit_of_measurement = coin

    @property
    def native_value(self) -> int | float:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
