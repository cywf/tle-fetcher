[![Nightly TLE refresh](https://github.com/cywf/tle-fetcher/actions/workflows/fetch-tles.yml/badge.svg)](https://github.com/cywf/tle-fetcher/actions/workflows/fetch-tles.yml)
# TLE Fetcher Utility

This repository contains a robust terminal-based utility for fetching up-to-date Two-Line Element (TLE) data for satellites from publicly available sources. It supports multiple data providers—CelesTrak and Ivan’s TLE API by default, with optional fallback to Space-Track and N2YO when credentials are provided. The tool can fetch single IDs interactively or process a batch of IDs from a queue file, validating and caching results.

## Requirements

- Python 3.x (tested with 3.8+).  
- Internet access to reach the TLE sources.  
- Optional: valid credentials for Space-Track (`SPACETRACK_USER`/`SPACETRACK_PASS`) and/or N2YO (`N2YO_API_KEY`) if you wish to use those services.

## Queueing and Batch Fetching

You can provide one or more NORAD catalog IDs on the command line, or point the script at a text file containing IDs (one per line). Blank lines and lines starting with `#` are ignored. An example file, `ids.txt`, is included in the repository:

```
# Queue of NORAD catalog IDs (one per line). Lines starting with '#' are ignored.
25544   # ISS (ZARYA)
43013   # TESS
```

```
# Queue of NORAD catalog IDs (one per line). Lines starting with '#' are ignored.
25544   # ISS (ZARYA)
43013   # TESS
```

To fetch TLEs for all IDs in a file and save them into the `tles/` directory, run:

```
python -m tle_fetcher fetch --ids-file ids.txt --source-order celestrak,ivan --no-name -o "tles/{id}.tle"
```

The `--source-order` flag controls which sources are queried first. When using the `-o` pattern, placeholders `{id}`, `{name}`, and `{epoch}` are substituted for the actual values. The `--no-name` flag omits satellite names from the file content.

## Running Manually

Interactive mode is still supported for ad-hoc lookups. Run:

```
python -m tle_fetcher fetch
```

and follow the prompts. You can also specify one or more IDs directly:

```
python -m tle_fetcher fetch 25544 43013 --source-order celestrak,ivan --quiet
```

## Automated TLE Refresh via GitHub Actions

A GitHub Actions workflow (`.github/workflows/fetch-tles.yml`) is included. It can be triggered manually (`workflow_dispatch`) or runs nightly at 03:27 UTC. Scheduled workflows use POSIX cron syntax and always run on the latest commit of the default branch. The job performs two passes:

1. Fetch TLEs for all IDs in `ids.txt` from public sources (CelesTrak and Ivan API).  
2. If secrets for Space-Track or N2YO are configured, fetch using those sources with verification. Secrets are masked in the logs.

Fetched TLEs are stored under the `tles/` directory. The workflow commits updated `.tle` files back to the repository only when there are actual changes. Concurrency is configured so that only one nightly run executes at a time.

To trigger the workflow manually, go to the **Actions** tab on GitHub, select **Nightly TLE refresh**, and click **Run workflow**.

## Adding New IDs

To add new satellites to the nightly refresh queue:

1. Edit `ids.txt` and append the new NORAD catalog ID on its own line. Comments beginning with `#` are allowed.  
2. Commit the change to the repository. The next scheduled run (or a manual run) will fetch and update the corresponding TLE files.

## Rotating Secrets

If you use Space-Track or N2YO, store your credentials as repository secrets (`SPACETRACK_USER`, `SPACETRACK_PASS`, and/or `N2YO_API_KEY`). To rotate them:

1. Open the repository **Settings** → **Secrets and variables** → **Actions**.  
2. Update the secret values.  
3. Future workflow runs will use the new credentials automatically.

## Data Sources

This tool queries open TLE data sources such as CelesTrak and Ivan Stanojević’s TLE API. When configured, it also queries Space-Track and N2YO for cross-validation. Please respect each provider’s terms of service.

## Catalogue discovery workflow

For bulk catalogue refreshes use the discovery pipeline, which persists
entire source responses inside `data/ingest.sqlite3` for offline reuse.
Run it via the new sub-command:

```
python -m tle_fetcher discover --source celestrak
```

Key flags:

- `--source` selects the upstream catalogue (default: `celestrak`).
- `--since` filters out entries whose epochs are at or before the
  provided ISO timestamp. When omitted the pipeline resumes from the
  last recorded cursor.
- `--offline` prevents network access and reuses the cached payload. The
  command fails if the requested source/since combination has not been
  cached previously.

Each pipeline execution records a row in the `runs` table alongside a
deduplicated list of new entries, making repeated runs idempotent. The
database doubles as a local mirror of the last successful catalogue
snapshot, enabling quick discovery even without connectivity.

To fetch TLEs for all IDs in a file and save them into the `tles/` directory, run:

```
python -m tle_fetcher fetch --ids-file ids.txt --source-order celestrak,ivan --no-name -o "tles/{id}.tle"
```

The `--source-order` flag controls which sources are queried first. When using the `-o` pattern, placeholders `{id}`, `{name}`, and `{epoch}` are substituted for the actual values. The `--no-name` flag omits satellite names from the file content.

## Running Manually

Interactive mode is still supported for ad-hoc lookups. Run:

```
python -m tle_fetcher fetch
```

and follow the prompts. You can also specify one or more IDs directly:

```
python -m tle_fetcher fetch 25544 43013 --source-order celestrak,ivan --quiet
```

## Automated TLE Refresh via GitHub Actions

A GitHub Actions workflow (`.github/workflows/fetch-tles.yml`) is included. It can be triggered manually (`workflow_dispatch`) or runs nightly at 03:27 UTC. Scheduled workflows use POSIX cron syntax and always run on the latest commit of the default branch. The job performs two passes:

1. Fetch TLEs for all IDs in `ids.txt` from public sources (CelesTrak and Ivan API).  
2. If secrets for Space-Track or N2YO are configured, fetch using those sources with verification. Secrets are masked in the logs.

Fetched TLEs are stored under the `tles/` directory. The workflow commits updated `.tle` files back to the repository only when there are actual changes. Concurrency is configured so that only one nightly run executes at a time.

To trigger the workflow manually, go to the **Actions** tab on GitHub, select **Nightly TLE refresh**, and click **Run workflow**.

## Adding New IDs

To add new satellites to the nightly refresh queue:

1. Edit `ids.txt` and append the new NORAD catalog ID on its own line. Comments beginning with `#` are allowed.  
2. Commit the change to the repository. The next scheduled run (or a manual run) will fetch and update the corresponding TLE files.

## Rotating Secrets

If you use Space-Track or N2YO, store your credentials as repository secrets (`SPACETRACK_USER`, `SPACETRACK_PASS`, and/or `N2YO_API_KEY`). To rotate them:

1. Open the repository **Settings** → **Secrets and variables** → **Actions**.  
2. Update the secret values.  
3. Future workflow runs will use the new credentials automatically.

## Data Sources

This tool queries open TLE data sources such as CelesTrak and Ivan Stanojević’s TLE API. When configured, it also queries Space-Track and N2YO for cross-validation. Please respect each provider’s terms of service.
