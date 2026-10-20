"""Tests for the Kryptex API helpers."""

from custom_components.kryptex_pool.api import (
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
