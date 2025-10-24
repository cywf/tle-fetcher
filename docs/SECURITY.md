# Security

This document highlights the major security considerations for the TLE Fetcher
project.

## Secrets management

- **Environment variables.** The CLI reads `SPACETRACK_USER`, `SPACETRACK_PASS`,
  and `N2YO_API_KEY` from the environment at runtime. Do not hard-code these
  values in scripts or configuration files.
- **GitHub Actions secrets.** Store production credentials using the repository
  settings panel (`Settings → Secrets and variables → Actions`). Workflows load
  the secrets at job runtime and never write them to disk.
- **Local development.** Prefer `.env` files tracked outside the repository or a
  password manager capable of injecting environment variables for each session.

## Network boundaries

- Outbound calls are made over HTTPS using Python’s standard `urllib` stack.
- Requests set a custom `User-Agent` so upstream providers can monitor traffic.
- The CLI does not expose network services; it is safe to run on developer
  workstations or CI machines with outbound internet access.

## Data handling

- TLE data is public but should still be validated. The CLI enforces checksum
  verification and ensures catalog numbers match the requested ID.
- Cached files are stored as plain text under `~/.cache/tle-fetcher`. When
  operating on shared machines ensure filesystem permissions restrict other
  users from tampering with cache contents.

## Dependency policy

- The repository avoids third-party runtime dependencies, relying solely on the
  Python standard library. Keep this policy when adding features to reduce the
  attack surface and simplify patching.
- When dependencies become necessary for documentation or tooling, pin versions
  inside the relevant workflow step or requirements file and review changelogs
  before upgrading.

## Vulnerability disclosure

Report suspected vulnerabilities by opening a security advisory on GitHub or
emailing the maintainer listed in the repository metadata. Provide steps to
reproduce and any logs that demonstrate impact. Expect an acknowledgement within
three business days.
