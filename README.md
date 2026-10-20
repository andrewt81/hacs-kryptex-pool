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

## Balance availability and Kryptex account identifiers

Kryptex supports two different mining modes, and the data exposed by the public
Pool API depends on the identifier used during setup:

- **Direct wallet mining:** when a regular cryptocurrency wallet address is used,
  the public API normally exposes the pool balance, payout threshold, workers, and
  hashrate data.
- **Kryptex account mining:** identifiers beginning with `krx` are Mining Usernames,
  not cryptocurrency wallet addresses. Earnings are converted and stored in the
  private Kryptex account balance. Kryptex returns HTTP 403 for the public balance
  and aggregate hashrate endpoints for these identifiers.

When a `krx` Mining Username is configured, the integration continues to provide
the data that Kryptex exposes publicly, including workers and their activity. The
balance sensors are marked unavailable instead of displaying an incorrect zero or
preventing the integration from loading.

Kryptex does not currently document a public authenticated API for reading the
private account balance. The balance must therefore be viewed in the Kryptex
website or mobile app. The integration does not request or store Kryptex account
credentials, browser cookies, or private tokens.

## Manual installation

Copy `custom_components/kryptex_pool` into the `custom_components` directory of your Home Assistant configuration, then restart Home Assistant.

## Support the project

If this integration is useful to you, you can [support its development with an optional cryptocurrency donation](DONATE.md). Donations do not unlock features or affect support.

## License

MIT
