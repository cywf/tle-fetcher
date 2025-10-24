# Secret Management & Operational Safety

## Storing Source Credentials

Some upstream providers (Space-Track, N2YO) require credentials. Store them as
GitHub Actions secrets or environment variables on the host that runs the
fetcher. Recommended variable names:

- `SPACETRACK_USER` / `SPACETRACK_PASS`
- `N2YO_API_KEY`

Never commit these secrets to the repository. When running in CI, configure the
secrets via **Settings → Secrets and variables → Actions**. Locally, prefer a
`.env` file that is ignored by version control or export variables per session.

## Offline Mode

Set `TLE_FETCHER_OFFLINE=1` (or pass `--offline`) to force the CLI to operate
without network access. In offline mode the fetcher falls back to cached TLEs in
`$TLE_FETCHER_STATE_DIR` (default: `~/.cache/tle-fetcher/db`). If no cached copy
is available the command exits with an error instead of silently returning
stale/empty data.

## Stale Data Warnings

The CLI emits warnings on stderr when returning a TLE that is older than the
requested cache TTL. This helps surface stale records during offline operation
or extended outages. Treat such warnings as prompts to re-enable connectivity
and refresh the cache.
