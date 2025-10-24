# TLE Fetcher Utility

[![Nightly TLE refresh](https://github.com/cywf/tle-fetcher/actions/workflows/fetch-tles.yml/badge.svg)](https://github.com/cywf/tle-fetcher/actions/workflows/fetch-tles.yml)

TLE Fetcher is a terminal-first assistant for downloading current Two-Line Elements
(TLEs) for satellites from public and authenticated providers. It prioritises robust
retrieval—retrying requests, validating checksums, and caching responses locally—so
you can keep working even when the network is unreliable.

## Features

- **Multi-source resolution.** Query CelesTrak and Ivan Stanojević’s public API by
  default, with optional fallbacks to Space-Track and N2YO when credentials are
  supplied.
- **Offline-aware caching.** Results are cached under `~/.cache/tle-fetcher` for two
  hours, allowing you to re-run commands or work without connectivity after an
  initial sync.
- **Batch and ad-hoc operation.** Provide one or more NORAD catalog IDs directly on
  the command line or by pointing at a queue file.
- **Flexible exports.** Write results to stdout, save per-satellite files, or emit
  the canonical three-line format (name + two TLE lines).

## Offline-first quickstart

The quickest path to a reliable offline cache is to prefetch your queue while
online, then rely on the local cache for subsequent lookups.

1. **Install the CLI** (see [Installation](#installation)).

1. **Stage the IDs** you care about by listing them in `ids.txt` (one per line,
   `#` comments allowed).

1. **Prefetch while online** to seed the cache and write export files:

   ```bash
   python3 tle_fetcher.py --ids-file ids.txt --source-order celestrak,ivan -o "tles/{id}.tle"
   ```

   Each lookup is cached in `~/.cache/tle-fetcher` and also saved in `tles/`.

1. **Work offline**—repeat the same command (or query individual IDs) without an
   internet connection. Cached entries will be returned transparently; the CLI
   exits non-zero only if a cache entry is missing or expired.

1. **Refresh when convenient** by re-running the fetch command while online. Fresh
   responses automatically overwrite the cached copy and any export files.

## Installation

These instructions assume Python 3.8 or newer is available. Replace `python3`
with `python` on Windows if required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

With the environment activated you can execute the script directly:

```bash
python3 tle_fetcher.py --help
```

Optional credentials can be supplied via environment variables to unlock premium
sources:

- `SPACETRACK_USER` / `SPACETRACK_PASS` – enables the Space-Track fallback.
- `N2YO_API_KEY` – enables the N2YO fallback.

## Command-line examples

Run the interactive prompt for a single ID:

```bash
python3 tle_fetcher.py
```

Fetch one or more NORAD IDs non-interactively and print to stdout:

```bash
python3 tle_fetcher.py 25544 43013 --source-order celestrak,ivan --quiet
```

Resolve IDs listed in a queue file and write each TLE to a dedicated file that
includes the satellite name when available:

```bash
python3 tle_fetcher.py --ids-file ids.txt --no-name -o "tles/{id}-{epoch}.tle"
```

Preview the export path substitutions supported by the `-o/--output-pattern`
flag:

| Placeholder | Description |
|-------------|----------------------------------|
| `{id}` | NORAD catalog identifier |
| `{name}` | Sanitised satellite name |
| `{epoch}` | ISO 8601 timestamp of the TLE |
| `{source}` | Provider that supplied the TLE |

Combine providers with caching disabled (useful for diagnostics):

```bash
python3 tle_fetcher.py 25544 --source-order celestrak,ivan,n2yo --cache-ttl 0 --verbose
```

## Automating with GitHub Actions

The repository ships with `.github/workflows/fetch-tles.yml`, a nightly workflow
scheduled for 03:27 UTC. It performs two passes:

1. Fetch IDs in `ids.txt` using public sources (CelesTrak + Ivan).
1. Retry with authenticated sources (Space-Track, N2YO) when the relevant
   secrets are available.

Outputs are written to `tles/` and committed back to the repository when they
change. Concurrency is limited so only one refresh runs at a time. Use
**Actions → Nightly TLE refresh → Run workflow** to trigger it manually.

## Contributing and further reading

Extended guidance lives in the `docs/` directory:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – module layout and data flow.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) – operational runbooks.
- [`docs/SECURITY.md`](docs/SECURITY.md) – credential management guidance.
- [`docs/CONNECTORS.md`](docs/CONNECTORS.md) – source-specific notes.
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) – contribution workflow.
- [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) – history of published
  upgrades.

We welcome pull requests and issue reports—see the contribution guide for
coding standards and review expectations.
