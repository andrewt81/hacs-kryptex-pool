# Kryptex Pool

Custom Home Assistant integration for the public Kryptex Pool API.

## Features

- Confirmed, unconfirmed, total, and lifetime paid balances
- Active and online worker counts
- Reported total hashrate
- Cloud polling every 60 seconds
- UI configuration by coin symbol and mining wallet address

## Installation

1. In HACS, add this repository as a custom repository with category **Integration**.
2. Install **Kryptex Pool** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and select **Kryptex Pool**.
4. Enter the coin symbol used by the pool (for example `RVN`) and the mining wallet address.

The integration uses Kryptex Pool's public, read-only API. No password or API token is required.

## Manual installation

Copy `custom_components/kryptex_pool` into the `custom_components` directory of your Home Assistant configuration, then restart Home Assistant.

## License

MIT
