# Connectors

Each connector wraps an upstream API and converts the response into the canonical
`TLE` dataclass. All connectors call the shared `http_get` helper for retries and
timeouts.

## CelesTrak (`celestrak`)

- **Endpoint:** `https://celestrak.org/NORAD/elements/gp.php?CATNR={id}&FORMAT=tle`
- **Authentication:** none
- **Response format:** plain-text three-line TLE; occasionally includes a leading
  name line.
- **Notes:** most resilient source; position it first in `--source-order` unless a
  premium provider is required for validation.

## Ivan Stanojević (`ivan`)

- **Endpoint:** `https://tle.ivanstanojevic.me/satellite/{id}`
- **Authentication:** none
- **Response format:** JSON dictionary with `name`, `line1`, and `line2` fields.
- **Notes:** parsing logic falls back to JSON when standard text detection fails.

## Space-Track (`spacetrack`)

- **Endpoint:** `https://www.space-track.org/basicspacedata/query/class/gp/NORAD_CAT_ID/{id}`
- **Authentication:** requires `SPACETRACK_USER` and `SPACETRACK_PASS` environment
  variables. Credentials must have API access enabled.
- **Response format:** JSON; the CLI extracts the first element and renders the
  three-line TLE.
- **Notes:** rate limited; keep it late in the source order to avoid unnecessary
  authentication calls when public sources succeed.

## N2YO (`n2yo`)

- **Endpoint:** `https://api.n2yo.com/rest/v1/satellite/tle/{id}&apiKey={N2YO_API_KEY}`
- **Authentication:** requires `N2YO_API_KEY`.
- **Response format:** JSON dictionary containing `tle`, `line1`, `line2`, and
  metadata.
- **Notes:** helpful for redundancy but subject to API key quotas. Respect per-day
  limits and monitor usage if the connector is routinely invoked.

## Source ordering tips

- The CLI accepts comma-separated aliases via `--source-order`. Only connectors
  named in that list are attempted.
- Configure authenticated sources in the workflow environment before adding them
  to automation, otherwise steps will fail with HTTP 401 responses.
- When running offline the cache is treated as an implicit connector. Set
  `--cache-ttl` to a large value to reuse cached entries longer.
