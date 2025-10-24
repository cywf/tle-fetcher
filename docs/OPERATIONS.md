# Operations Guide

This document captures the high-level workflows for the TLE Fetcher utility.

## CLI Usage

```bash
python tle_fetcher.py --help
```

Key options:

- `--mode {fetch,report}` – switch between live retrievals and offline reporting.
- `--db-path PATH` – override the cache/database directory. Defaults to
  `~/.cache/tle-fetcher`.
- `--log-level LEVEL` – configure logging verbosity (`DEBUG`, `INFO`, etc.).
- `--ids` / `--ids-file` – provide NORAD catalog identifiers either inline or via a
  comment-friendly file.
- `--report [DEST]` – when paired with `--mode report`, emit a JSON summary to `DEST`
  (or to stdout when omitted).

Example batch fetch using a file:

```bash
python tle_fetcher.py --mode fetch --ids-file ids.txt --output tles/{id}.tle
```

Generate a report for the current cache and save it to disk:

```bash
python tle_fetcher.py --mode report --report tmp/report.json
```

## Offline Runbook

When internet connectivity is unavailable you can still audit the latest cached
Two-Line Elements (TLEs):

1. Ensure the cache directory is available locally. If it was previously synced
   from another machine, point the CLI at it using `--db-path`.
2. Run the reporting mode to generate a JSON snapshot of cached TLEs:

   ```bash
   python tle_fetcher.py --mode report --db-path /mnt/cache --report -
   ```

3. Inspect the resulting JSON for metadata such as NORAD IDs, epoch timestamps
   and file locations.
4. Optionally archive the generated report for later comparison or incident
   reviews.
