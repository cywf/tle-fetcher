# Connector setup

This project includes optional connectors that integrate the TLE fetcher with
external services. Each connector is guarded by feature flags and environment
variables so the default behaviour (standalone TLE fetching) continues to work
without additional configuration.

## Notion database synchronisation

The `sync` CLI sub-command can export data from a Notion database to a local
JSON file or import JSON records into the database. The command is intentionally
safe-by-default: if credentials are missing or the Notion API is unreachable the
operation is skipped with an informative log message.

### Configuration

| Environment variable | Description |
| --- | --- |
| `TLE_FETCHER_NOTION_TOKEN` | Integration token with access to the target database. |
| `TLE_FETCHER_NOTION_DATABASE_ID` | Identifier of the Notion database to read/write. |
| `TLE_FETCHER_FEATURE_NOTION_SYNC` | Optional flag (`true/false`) to force-enable or disable the connector. |
| `TLE_FETCHER_NOTION_TIMEOUT` | Optional HTTP timeout (seconds). |
| `TLE_FETCHER_DATA_DIR` | Override for the data directory used by the CLI (defaults to `<repo>/data`). |

Secrets are redacted in logs by default. If the feature flag is not set the
connector automatically enables itself when both credentials are present.

### Usage

Pull records from Notion into `data/notion_dump.json`:

```bash
python tle_fetcher.py sync --target notion --mode pull
```

Push records from the same file into Notion:

```bash
python tle_fetcher.py sync --target notion --mode push
```

The file must contain either a list of property mappings or a JSON object with
`results` (mirroring the output of the pull step). Each record is sent as a page
creation request targeting the configured database.

To perform both operations in sequence, use `--mode both`. Additional options:

* `--output PATH` – destination file for pull results (defaults to
  `data/notion_dump.json`).
* `--input PATH` – source file for pushes (defaults to the same path).
* `--page-size` – number of rows requested per pull call.
* `--limit` – limit the number of records pushed in a single invocation.

If the connector is disabled or the network is unavailable, the command exits
successfully and logs the reason for the skip without raising an error.
