# Architecture Overview

The `tle_fetcher` project is migrating toward a package-oriented layout.
The `tle_fetcher.cli` package now owns the legacy command-line logic,
while the root-level `tle_fetcher.py` module remains a thin wrapper for
backwards compatibility. This transition allows the team to introduce
new submodules (cache, policy, sources) without disrupting existing
workflows.

## Components

- **CLI Facade** (`tle_fetcher.cli`): Houses the CLI orchestration code
  and exposes `bootstrap_cli()` for reuse in scripts and tests.
- **Legacy CLI Implementation** (`tle_fetcher.cli.legacy`): All
  historically-proven logic that performs fetching, caching and output
  management.
- **Package Entry Point** (`tle_fetcher.__init__`): Provides
  `tle_fetcher.main()` for module execution and re-exports
  `bootstrap_cli` for consumers.
- **Legacy Script** (`tle_fetcher.py`): Maintained for users invoking the
  repo directly or via existing automation; delegates to the package.

## Offline-First Mandate

The offline-first specification (see `docs/specs/offline_first_system.md`)
forces the data plane to prioritise cache lookups, record provenance, and
only reach remote providers after exhausting local options. Any new
module must respect the spec-defined interfaces and return types.

## CLI Contract

The CLI consumes `argparse` to maintain existing flags. `bootstrap_cli`
accepts an optional `argv` sequence, enabling tests or future service
wrappers to exercise the CLI without patching global state. Exit codes
remain consistent with the legacy behaviour to avoid breaking scripts.
