# Contributing

Thanks for helping improve **tle-fetcher**! This project ships a small but
feature-rich Python CLI. The GitHub Actions workflows enforce quality gates and
provide nightly smoke coverage, so please make sure local changes pass the same
checks before opening a pull request.

## Development environment

1. Create a virtual environment with Python 3.11 (or newer).
2. Install the dev tools:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

3. Optionally install the Rust toolchain (`rustup`) if you plan to work on the
   future native extensions.

## Required checks

The main CI workflow runs on Linux, macOS, and Windows. Every PR must pass the
following commands locally:

```bash
ruff check
mypy tle_fetcher.py
python -m pytest -q
```

These mirror the `lint`, `type-check`, and `test` stages that CI executes via
`.github/workflows/ci.yml`. The workflow also primes pip caches and stores the
pytest JUnit XML report as an artifact for each platform.

If a `Cargo.toml` file is present, CI additionally runs `cargo fmt --check`,
`cargo check --all-targets`, and `cargo test` across the same OS matrix.

## Nightly smoke tests

The scheduled workflow (`.github/workflows/nightly-smoke.yml`) seeds the CLI’s
cache with fixtures under `data/cache/` and runs two smoke commands:

- JSON fetch for a single NORAD ID.
- Batch fetch using `data/cache/smoke_ids.txt` that writes sanitized TLEs to
  `smoke-out/`.

Artifacts from the smoke job are uploaded for quick inspection. If you change
CLI behaviour that affects cache layout or output, update the fixtures in
`data/cache/` accordingly.

## Release builds

Tagged releases (`v*`) trigger `.github/workflows/release.yml`, which uses
[Maturin](https://github.com/PyO3/maturin) to build Python wheels from any Rust
extension crate in the repository. The job installs the Rust toolchain, reuses
Cargo caches, and uploads the compiled wheels both as workflow artifacts and as
assets on the GitHub release page.

Before tagging a release, verify the native build locally:

```bash
maturin build --release
```

## Commit style

- Keep commits focused and include descriptive messages.
- Run the formatting/lint commands above before committing.
- Prefer small, reviewable pull requests.

Thank you for contributing!
