"""Constants for Kryptex Pool."""

from datetime import timedelta

DOMAIN = "kryptex_pool"
CONF_COIN = "coin"
CONF_ADDRESS = "address"
API_BASE_URL = "https://pool.kryptex.com"
SCAN_INTERVAL = timedelta(seconds=60)


def is_kryptex_account(address: str) -> bool:
    """Return whether an address is a Kryptex Mining Username."""
    return address.strip().lower().startswith("krx")
