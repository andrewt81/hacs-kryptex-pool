"""Tests for the Kryptex API helpers."""

import asyncio
import sys

import pytest

from custom_components.kryptex_pool.api import (
    KryptexAPIError,
    KryptexClient,
    extract_workers,
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


def test_worker_helpers_support_current_kryptex_payload() -> None:
    worker = {
        "worker": "N37",
        "scheme": "pps",
        "status": "online",
        "last_share": 1_792_454_632_813,
        "valid": 156,
        "stale": 1,
        "invalid": 0,
        "avg_hashrate_24h": "21266998240360.68",
        "avg_hashrate_3h": "20000000000000",
        "avg_hashrate_30m": "19000000000000",
        "agent": "SRBMiner-MULTI/3.7.7",
        "server_geo": "eu",
    }

    assert worker_identity(worker) == "N37|pps"
    assert worker_name(worker) == "N37"
    assert worker_scheme(worker) == "PPS"
    assert worker_hashrate(worker) == 19_000_000_000_000
    assert worker_hashrate_period(worker, "24h") == 21_266_998_240_360.68
    assert worker_shares(worker, "valid") == 156
    assert worker_last_share(worker) == 1_792_454_632_813
    assert worker_agent(worker) == "SRBMiner-MULTI/3.7.7"
    assert worker_server_region(worker) == "EU"


def test_hashrate_scale_selects_readable_si_unit() -> None:
    assert hashrate_scale(999) == (1, "H/s")
    assert hashrate_scale(1_000) == (1_000, "kH/s")
    assert hashrate_scale(1_000_000_000_000) == (1_000_000_000_000, "TH/s")
    assert hashrate_scale(100_000_000_000_000) == (1_000_000_000_000, "TH/s")


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
