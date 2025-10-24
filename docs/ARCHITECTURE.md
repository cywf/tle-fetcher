# Architecture

This document describes how the TLE Fetcher CLI is structured so that new
contributors can reason about control flow, caching, and source integrations.

## High-level components

```
┌──────────────────┐     ┌──────────────────────┐
│ Command-line CLI │ ──▶ │ Fetch coordinator    │
└──────────────────┘     │  • argument parsing  │
                         │  • source ordering   │
                         └─────────┬────────────┘
                                   │
                         ┌─────────▼────────────┐
                         │ Source adapters      │
                         │  • celestrak         │
                         │  • ivan              │
                         │  • spacetrack        │
                         │  • n2yo              │
                         └─────────┬────────────┘
                                   │
                         ┌─────────▼────────────┐
                         │ Validation & parsing │
                         │  • checksum          │
                         │  • epoch handling    │
                         └─────────┬────────────┘
                                   │
                         ┌─────────▼────────────┐
                         │ Cache manager        │
                         │  • filesystem store  │
                         │  • TTL enforcement   │
                         └──────────────────────┘
```

- **Command-line CLI** — `tle_fetcher.py` is both the module entry point and the
  command dispatcher. Argument parsing uses `argparse` and produces an ordered
  list of NORAD IDs to fetch.
- **Fetch coordinator** — orchestrates lookups. It optionally consults the cache
  before invoking HTTP adapters, retries on transient errors, and stops once a
  valid TLE has been retrieved.
- **Source adapters** — one function per upstream, each responsible for building
  the correct URL and decoding the response format. The adapters share the
  low-level `http_get` helper which implements retries, jitter, and a custom
  `User-Agent` header.
- **Validation & parsing** — converts raw responses into the canonical `TLE`
  dataclass by verifying checksums, matching catalog numbers, and normalising the
  epoch.
- **Cache manager** — persists successful fetches to
  `~/.cache/tle-fetcher/<id>.tle`. Cache entries are reused until their TTL
  expires.

## Execution flow

1. The CLI resolves the ordered list of NORAD IDs from arguments or a queue file
   (ignoring blank lines and comments).
1. For each ID the cache manager is consulted. When the cached entry is valid it
   is emitted immediately unless `--cache-ttl 0` disables caching.
1. If no cache hit is available the fetch coordinator iterates through the
   source list provided via `--source-order`. For each adapter the HTTP helper is
   called with exponential backoff.
1. After a successful fetch the TLE is validated, persisted via `write_cache`,
   and optionally written to the user-specified output path.
1. Aggregated results are printed, exported, or returned through the CLI exit
   code.

## Error handling

- HTTP failures are retried with backoff and jitter to avoid thundering herds.
- Validation failures short-circuit the adapter and continue to the next source.
- Fatal conditions (e.g. invalid CLI arguments, missing cache with offline-only
  mode) raise exceptions that translate to non-zero exit codes.

## Extending the system

1. **Adding a connector** — implement `fetch_<provider>` mirroring the existing
   functions. Ensure responses are parsed through `parse_tle_text` to reuse
   validation logic, and extend `SOURCE_ALIASES` if the CLI should recognise a
   short-hand name.
1. **Changing caching behaviour** — adjust `CACHE_TTL_SECS` or extend the cache
   helper functions. Any changes should keep the cache directory path stable to
   preserve offline usability.
1. **Embedding the CLI** — import `fetch_for_ids` (or similar helper) from
   `tle_fetcher.py` to reuse orchestration logic in other tools. The CLI is
   intentionally modular so modules can be imported without executing the
   interactive prompt.
