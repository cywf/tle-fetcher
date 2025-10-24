# Contributing Guide

## Workflow

1. Start by reading the specification documents inside `docs/specs/` to
   understand the offline-first expectations.
2. Update or author specs before shipping major behaviour changes. The
   repo favours documentation-first development.
3. Implement the change in the `tle_fetcher` package. If you need to
   touch the legacy shim (`tle_fetcher.py`), keep it minimal and delegate
   into the package modules.
4. Add or update tests under `tests/`, including smoke CLI tests.
5. Run the lint/check GitHub Action locally if possible, or rely on CI.

## Coding Standards

- Prefer pure functions where feasible to simplify offline testing.
- Honour the CLI contract defined in `docs/specs/offline_first_system.md`.
- Avoid new runtime dependencies unless the spec explicitly demands
  them; stick with the Python standard library or PyO3 extensions.

## Commit Expectations

- Each commit should update documentation when behaviour changes.
- Include regression tests for bugs and integration tests for new CLI
  flows.
- Keep pull requests focused; the GitHub Action will provide quick
  feedback on placeholder lint/check runs.
