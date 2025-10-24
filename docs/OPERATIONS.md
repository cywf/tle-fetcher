# Operations

This runbook documents the day-to-day operational tasks required to keep the TLE
Fetcher service healthy in both local and automated environments.

## Daily/weekly tasks

- **Review automated runs.** Inspect the *Nightly TLE refresh* workflow summary
  for failures or degraded timings. Logs live in GitHub Actions → Workflow runs.
- **Rotate credentials quarterly.** Update the `SPACETRACK_*` and `N2YO_API_KEY`
  secrets in the repository settings. The CLI loads them from the environment so
  no code changes are needed.
- **Prune stale cache entries.** Cached files older than the configured TTL are
  ignored automatically, but you can delete `~/.cache/tle-fetcher` periodically if
  disk space is limited.

## Incident response

1. **CLI errors on a single machine**

   - Re-run with `--verbose --cache-ttl 0` to gather HTTP details.
   - Confirm upstream availability using `curl` and the URLs documented in
     [`docs/CONNECTORS.md`](./CONNECTORS.md).
   - If an upstream outage is confirmed, temporarily reorder sources using
     `--source-order` to prioritise healthy providers.

1. **Automation failure (GitHub Actions)**

   - Download workflow logs to determine which step failed.
   - Validate that secrets remain configured on the repository and have not
     expired.
   - Re-run the workflow manually after addressing the underlying issue.

1. **Data integrity concerns**

   - Validate the cached file by running `python3 tle_fetcher.py <id> --verbose`
     and checking checksum validation output.
   - Compare with the authoritative source using the relevant connector endpoint.

## Monitoring hooks

- The CLI exits non-zero when no sources succeed or when validation fails. Use
  that exit code inside scripts to trigger alerts.
- Workflow badges and job summaries surface high-level status for scheduled runs.
- Logs for each connector include the provider name, response status, and retry
  counts when `--verbose` is enabled.

## Deployment checklist

1. Ensure the Python version on the target system is ≥ 3.8.
1. Copy `ids.txt` and any supporting scripts to the execution directory.
1. Export required credentials (`SPACETRACK_USER`, `SPACETRACK_PASS`,
   `N2YO_API_KEY`) into the runtime environment or secret store.
1. Run the quickstart fetch command from the [README](../README.md) while online.
1. Confirm the cache directory now contains one file per ID.
1. Document the installation location and schedule in your internal inventory.
