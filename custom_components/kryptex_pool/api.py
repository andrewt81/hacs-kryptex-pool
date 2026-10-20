"""Asynchronous client for the public Kryptex Pool API."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import API_BASE_URL


class KryptexAPIError(Exception):
    """Error raised when the Kryptex API cannot be read."""


def extract_workers(payload: Any) -> list[dict[str, Any]]:
    """Extract workers from current and older API response envelopes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("workers", "data", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_workers(value)
            if nested:
                return nested
    return []


def numeric_value(payload: dict[str, Any], *paths: str) -> float:
    """Get the first numeric value from dotted paths."""
    for path in paths:
        value: Any = payload
        for key in path.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
    return 0.0


def worker_is_online(worker: dict[str, Any]) -> bool:
    """Return whether a Kryptex worker is online."""
    for key in ("online", "isOnline", "is_online", "active"):
        if isinstance(worker.get(key), bool):
            return worker[key]
    return str(worker.get("status", "")).lower() in {"online", "active", "working"}


def worker_hashrate(worker: dict[str, Any]) -> float:
    """Return the worker hashrate in hashes per second when available."""
    return numeric_value(
        worker,
        "hashrate",
        "hashRate",
        "hashrate.current",
        "hashrate.realtime",
        "stats.hashrate",
    )


class KryptexClient:
    """Read-only client for Kryptex Pool."""

    def __init__(self, session: ClientSession, coin: str, address: str) -> None:
        self._session = session
        self._coin = coin.lower()
        self._address = address

    async def _get_json(self, path: str) -> Any:
        try:
            async with self._session.get(
                f"{API_BASE_URL}{path}", timeout=20
            ) as response:
                response.raise_for_status()
                return await response.json()
        except (ClientError, ClientResponseError, TimeoutError, ValueError) as err:
            raise KryptexAPIError("Unable to communicate with Kryptex Pool") from err

    async def async_validate(self) -> None:
        """Validate the selected coin against the public API."""
        await self._get_json(f"/api/v1/coin/{quote(self._coin, safe='')}/info")

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch balance and workers in parallel."""
        coin = quote(self._coin, safe="")
        address = quote(self._address, safe="")
        balance, workers = await asyncio.gather(
            self._get_json(f"/{coin}/api/v1/miner/balance/{address}"),
            self._get_json(f"/{coin}/api/v3/miner/workers/{address}"),
        )
        return {
            "balance": balance if isinstance(balance, dict) else {},
            "workers": extract_workers(workers),
        }
