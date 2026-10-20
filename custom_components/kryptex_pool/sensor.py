"""Sensors for Kryptex Pool."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import (
    hashrate_scale,
    numeric_value,
    worker_agent,
    worker_hashrate,
    worker_hashrate_period,
    worker_identity,
    worker_is_online,
    worker_last_share,
    worker_name,
    worker_scheme,
    worker_server_region,
    worker_shares,
)
from .const import CONF_ADDRESS, CONF_COIN, DOMAIN, is_kryptex_account

Worker = dict[str, Any]
Coordinator = DataUpdateCoordinator[dict[str, Any]]


@dataclass(frozen=True, kw_only=True)
class KryptexSensorDescription(SensorEntityDescription):
    """Describe a Kryptex sensor."""

    value_fn: Callable[[dict[str, Any]], int | float]
    source: str
    coin_unit: bool = False
    hashrate: bool = False


@dataclass(frozen=True, kw_only=True)
class KryptexWorkerSensorDescription(SensorEntityDescription):
    """Describe a sensor belonging to one Kryptex worker."""

    value_fn: Callable[[Worker], int | float | str | datetime | None]
    hashrate: bool = False


SENSORS = (
    KryptexSensorDescription(
        key="confirmed",
        translation_key="confirmed",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL,
        source="balance",
        coin_unit=True,
        value_fn=lambda data: numeric_value(data["balance"], "confirmed"),
    ),
    KryptexSensorDescription(
        key="unconfirmed",
        translation_key="unconfirmed",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL,
        source="balance",
        coin_unit=True,
        value_fn=lambda data: numeric_value(data["balance"], "unconfirmed"),
    ),
    KryptexSensorDescription(
        key="total",
        translation_key="total",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL,
        source="balance",
        coin_unit=True,
        value_fn=lambda data: numeric_value(data["balance"], "total"),
    ),
    KryptexSensorDescription(
        key="paid",
        translation_key="paid",
        suggested_display_precision=8,
        state_class=SensorStateClass.TOTAL_INCREASING,
        source="balance",
        coin_unit=True,
        value_fn=lambda data: numeric_value(
            data["balance"], "miner.paidBalance", "paid", "paidBalance"
        ),
    ),
    KryptexSensorDescription(
        key="workers",
        translation_key="workers",
        source="workers",
        value_fn=lambda data: len(data["workers"]),
    ),
    KryptexSensorDescription(
        key="online_workers",
        translation_key="online_workers",
        source="workers",
        value_fn=lambda data: sum(
            worker_is_online(worker) for worker in data["workers"]
        ),
    ),
    KryptexSensorDescription(
        key="hashrate",
        translation_key="hashrate",
        suggested_display_precision=2,
        source="workers",
        hashrate=True,
        value_fn=lambda data: round(
            sum(worker_hashrate(worker) for worker in data["workers"]), 2
        ),
    ),
)


WORKER_SENSORS = (
    KryptexWorkerSensorDescription(
        key="status",
        translation_key="worker_status",
        icon="mdi:lan-connect",
        value_fn=lambda worker: "online" if worker_is_online(worker) else "offline",
    ),
    KryptexWorkerSensorDescription(
        key="scheme",
        translation_key="worker_scheme",
        icon="mdi:cash-sync",
        value_fn=worker_scheme,
    ),
    KryptexWorkerSensorDescription(
        key="hashrate_30m",
        translation_key="worker_hashrate_30m",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:speedometer",
        hashrate=True,
        value_fn=lambda worker: worker_hashrate_period(worker, "30m"),
    ),
    KryptexWorkerSensorDescription(
        key="hashrate_3h",
        translation_key="worker_hashrate_3h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:speedometer-medium",
        hashrate=True,
        value_fn=lambda worker: worker_hashrate_period(worker, "3h"),
    ),
    KryptexWorkerSensorDescription(
        key="hashrate_24h",
        translation_key="worker_hashrate_24h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:speedometer-slow",
        hashrate=True,
        value_fn=lambda worker: worker_hashrate_period(worker, "24h"),
    ),
    KryptexWorkerSensorDescription(
        key="valid_shares",
        translation_key="worker_valid_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:check-circle-outline",
        value_fn=lambda worker: worker_shares(worker, "valid"),
    ),
    KryptexWorkerSensorDescription(
        key="stale_shares",
        translation_key="worker_stale_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:clock-alert-outline",
        value_fn=lambda worker: worker_shares(worker, "stale"),
    ),
    KryptexWorkerSensorDescription(
        key="invalid_shares",
        translation_key="worker_invalid_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle-outline",
        value_fn=lambda worker: worker_shares(worker, "invalid"),
    ),
    KryptexWorkerSensorDescription(
        key="last_share",
        translation_key="worker_last_share",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-check-outline",
        value_fn=lambda worker: (
            datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            if (timestamp := worker_last_share(worker)) is not None
            else None
        ),
    ),
    KryptexWorkerSensorDescription(
        key="software",
        translation_key="worker_software",
        icon="mdi:application-cog-outline",
        value_fn=worker_agent,
    ),
    KryptexWorkerSensorDescription(
        key="server_region",
        translation_key="worker_server_region",
        icon="mdi:server-network",
        value_fn=worker_server_region,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up pool-wide and dynamically discovered worker sensors."""
    coordinator: Coordinator = entry.runtime_data
    async_add_entities(KryptexSensor(coordinator, entry, item) for item in SENSORS)

    added: set[tuple[str, str]] = set()

    def async_add_worker_entities() -> None:
        entities: list[SensorEntity] = []
        for worker in coordinator.data["workers"]:
            identifier = worker_identity(worker)
            if identifier is None:
                continue
            for description in WORKER_SENSORS:
                key = (identifier, description.key)
                if key in added:
                    continue
                added.add(key)
                entities.append(
                    KryptexWorkerSensor(
                        coordinator, entry, identifier, description
                    )
                )
        if entities:
            async_add_entities(entities)

    async_add_worker_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_worker_entities))


class KryptexSensor(CoordinatorEntity[Coordinator], SensorEntity):
    """A sensor backed by the shared Kryptex coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Coordinator,
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
        if description.source == "balance" and is_kryptex_account(address):
            self._attr_entity_registry_enabled_default = False
        self._hashrate_divisor = 1.0
        if description.hashrate:
            current_value = description.value_fn(coordinator.data)
            (
                self._hashrate_divisor,
                self._attr_native_unit_of_measurement,
            ) = hashrate_scale(float(current_value))

    @property
    def native_value(self) -> int | float:
        """Return the current sensor value."""
        value = self.entity_description.value_fn(self.coordinator.data)
        if self.entity_description.hashrate:
            return value / self._hashrate_divisor
        return value

    @property
    def available(self) -> bool:
        """Return whether the API source for this sensor is available."""
        source_available = self.coordinator.data.get(
            f"{self.entity_description.source}_available", True
        )
        return super().available and source_available


class KryptexWorkerEntity(CoordinatorEntity[Coordinator]):
    """Base class for entities belonging to a Kryptex worker."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: Coordinator, entry: ConfigEntry, identifier: str
    ) -> None:
        super().__init__(coordinator)
        self._identifier = identifier
        coin = str(entry.data[CONF_COIN])
        address = str(entry.data[CONF_ADDRESS])
        self._pool_device_id = f"{coin.lower()}_{address.lower()}"
        worker = self._worker
        display_name = worker_name(worker) if worker else "Worker"
        scheme = worker_scheme(worker) if worker else None
        device_name = f"{display_name} ({scheme})" if scheme else display_name
        encoded_identifier = quote(identifier, safe="")
        self._worker_device_id = (
            f"{self._pool_device_id}_worker_{encoded_identifier}"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._worker_device_id)},
            "name": device_name,
            "manufacturer": "Kryptex",
            "model": "Pool worker",
            "sw_version": worker_agent(worker) if worker else None,
            "via_device": (DOMAIN, self._pool_device_id),
        }

    @property
    def _worker(self) -> Worker | None:
        return next(
            (
                worker
                for worker in self.coordinator.data["workers"]
                if worker_identity(worker) == self._identifier
            ),
            None,
        )

    @property
    def available(self) -> bool:
        """Return whether this worker remains in the API response."""
        workers_available = self.coordinator.data.get("workers_available", True)
        return super().available and workers_available and self._worker is not None


class KryptexWorkerSensor(KryptexWorkerEntity, SensorEntity):
    """A sensor exposing one metric for a Kryptex worker."""

    def __init__(
        self,
        coordinator: Coordinator,
        entry: ConfigEntry,
        identifier: str,
        description: KryptexWorkerSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, identifier)
        self.entity_description = description
        self._attr_unique_id = f"{self._worker_device_id}_{description.key}"
        self._hashrate_divisor = 1.0
        if description.hashrate:
            worker = self._worker
            current_value = description.value_fn(worker) if worker else None
            numeric_value = (
                float(current_value)
                if isinstance(current_value, (int, float))
                else None
            )
            (
                self._hashrate_divisor,
                self._attr_native_unit_of_measurement,
            ) = hashrate_scale(numeric_value)

    @property
    def native_value(self) -> int | float | str | datetime | None:
        """Return the current worker metric."""
        worker = self._worker
        if worker is None:
            return None
        value = self.entity_description.value_fn(worker)
        if self.entity_description.hashrate and isinstance(value, (int, float)):
            return value / self._hashrate_divisor
        return value
