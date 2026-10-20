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
    """Return the best current worker hashrate in hashes per second."""
    return numeric_value(
        worker,
        "hashrate",
        "hashRate",
        "hashrate.current",
        "hashrate.realtime",
        "stats.hashrate",
        "avg_hashrate_30m",
        "avg_hashrate_3h",
        "avg_hashrate_24h",
    )


def worker_hashrate_period(worker: dict[str, Any], period: str) -> float:
    """Return a worker average hashrate for a Kryptex time period."""
    return numeric_value(worker, f"avg_hashrate_{period}")


def worker_identity(worker: dict[str, Any]) -> str | None:
    """Return a stable identity for a worker and payment scheme."""
    name = str(worker.get("worker") or worker.get("name") or "").strip()
    if not name:
        return None
    scheme = str(worker.get("scheme") or "default").strip().lower()
    return f"{name}|{scheme}"


def worker_name(worker: dict[str, Any]) -> str:
    """Return the display name of a Kryptex worker."""
    return str(worker.get("worker") or worker.get("name") or "Worker").strip()


def worker_scheme(worker: dict[str, Any]) -> str | None:
    """Return the worker payment scheme."""
    value = str(worker.get("scheme") or "").strip()
    return value.upper() or None


def worker_shares(worker: dict[str, Any], share_type: str) -> int:
    """Return a worker share counter."""
    return int(numeric_value(worker, share_type))


def worker_last_share(worker: dict[str, Any]) -> float | None:
    """Return the last share timestamp in milliseconds."""
    value = numeric_value(worker, "last_share", "lastShare")
    return value or None


def worker_agent(worker: dict[str, Any]) -> str | None:
    """Return the mining software reported by the worker."""
    value = str(worker.get("agent") or "").strip()
    return value or None


def worker_server_region(worker: dict[str, Any]) -> str | None:
    """Return the Kryptex server region used by the worker."""
    value = str(worker.get("server_geo") or worker.get("region") or "").strip()
    return value.upper() or None


def hashrate_scale(value: float | None) -> tuple[float, str]:
    """Return a readable divisor and SI unit for a hashrate in H/s."""
    magnitude = abs(value or 0)
    units = (
        (1_000_000_000_000_000_000, "EH/s"),
        (1_000_000_000_000_000, "PH/s"),
        (1_000_000_000_000, "TH/s"),
        (1_000_000_000, "GH/s"),
        (1_000_000, "MH/s"),
        (1_000, "kH/s"),
    )
    for divisor, unit in units:
        if magnitude >= divisor:
            return divisor, unit
    return 1, "H/s"


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
        """Fetch balance and workers, preserving any available partial data."""
        coin = quote(self._coin, safe="")
        address = quote(self._address, safe="")
        balance, workers = await asyncio.gather(
            self._get_json(f"/{coin}/api/v1/miner/balance/{address}"),
            self._get_json(f"/{coin}/api/v3/miner/workers/{address}"),
            return_exceptions=True,
        )

        balance_available = not isinstance(balance, Exception)
        workers_available = not isinstance(workers, Exception)
        if not balance_available and not workers_available:
            raise KryptexAPIError("Unable to communicate with Kryptex Pool")

        return {
            "balance": (
                balance
                if balance_available and isinstance(balance, dict)
                else {}
            ),
            "workers": extract_workers(workers) if workers_available else [],
            "balance_available": balance_available,
            "workers_available": workers_available,
        }
