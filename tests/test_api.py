"""Tests for the Kryptex API helpers."""

import asyncio
import sys

import pytest

from custom_components.kryptex_pool.api import (
    KryptexAPIError,
    KryptexClient,
    extract_workers,
    numeric_value,
    worker_hashrate,
    worker_is_online,
)


def test_extract_workers_from_nested_payload() -> None:
    workers = [{"name": "rig-1"}, {"name": "rig-2"}]
    assert extract_workers({"data": {"workers": workers}}) == workers


def test_numeric_value_supports_strings_and_nested_paths() -> None:
    payload = {"total": "1.25", "miner": {"paidBalance": 3}}
    assert numeric_value(payload, "total") == 1.25
    assert numeric_value(payload, "miner.paidBalance") == 3.0


def test_worker_helpers_accept_common_shapes() -> None:
    worker = {"status": "online", "hashrate": {"current": 1234.5}}
    assert worker_is_online(worker) is True
    assert worker_hashrate(worker) == 1234.5


def test_unknown_payload_is_safe() -> None:
    assert extract_workers(None) == []
    assert numeric_value({}, "missing") == 0.0
    assert worker_is_online({}) is False
    assert worker_hashrate({}) == 0.0


@pytest.mark.skipif(sys.platform == "win32", reason="Windows sandbox event loop")
def test_get_data_keeps_workers_when_balance_is_forbidden(monkeypatch) -> None:
    client = KryptexClient(None, "BTC", "wallet")  # type: ignore[arg-type]

    async def fake_get_json(path: str):
        if "/balance/" in path:
            raise KryptexAPIError("Unable to communicate with Kryptex Pool")
        return {"results": [{"worker": "rig-1", "hashrate": 1234}]}

    monkeypatch.setattr(client, "_get_json", fake_get_json)

    data = asyncio.run(client.async_get_data())

    assert data["balance"] == {}
    assert data["balance_available"] is False
    assert data["workers"] == [{"worker": "rig-1", "hashrate": 1234}]
    assert data["workers_available"] is True


@pytest.mark.skipif(sys.platform == "win32", reason="Windows sandbox event loop")
def test_get_data_fails_when_all_endpoints_fail(monkeypatch) -> None:
    client = KryptexClient(None, "BTC", "wallet")  # type: ignore[arg-type]

    async def fake_get_json(path: str):
        raise KryptexAPIError("Unable to communicate with Kryptex Pool")

    monkeypatch.setattr(client, "_get_json", fake_get_json)

    with pytest.raises(KryptexAPIError):
        asyncio.run(client.async_get_data())
