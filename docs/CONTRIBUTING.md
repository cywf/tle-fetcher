# Contributing

Thanks for your interest in improving TLE Fetcher! This guide explains how to
get started and how reviews are conducted.

## Development workflow

1. **Fork and clone** the repository.
1. **Create a virtual environment** and install dependencies if required for your
   change (`python3 -m venv .venv && source .venv/bin/activate`).
1. **Create a feature branch**: `git checkout -b feature/my-change`.
1. **Implement changes** following the [architecture](./ARCHITECTURE.md) and
   [security](./SECURITY.md) guidance.
1. **Format documentation** using `mdformat` (the CI step enforces this):
   `mdformat README.md docs/*.md`.
1. **Run tests** or manual checks relevant to your change. For CLI tweaks this may
   involve invoking `python3 tle_fetcher.py --help` or executing sample commands.
1. **Commit with context**, referencing issues when applicable.
1. **Open a pull request** describing the change, motivation, and any operational
   considerations.

## Code style

- The codebase adheres to Python’s standard library; avoid introducing
  third-party runtime dependencies without discussion.
- Prefer explicit imports and keep helper functions near their callers inside
  `tle_fetcher.py` unless reuse warrants refactoring into modules.
- Raise descriptive exceptions rather than returning sentinel values.

## Documentation expectations

- Update the README and affected documents under `docs/` when behaviour changes.
- Include command examples whenever new flags or output formats are introduced.
- Keep release notes current; each feature or bug fix should add a short entry to
  [`docs/RELEASE_NOTES.md`](./RELEASE_NOTES.md).

## Communication

- Use GitHub Discussions or Issues to propose significant enhancements.
- Security-sensitive reports should follow the process in
  [`docs/SECURITY.md`](./SECURITY.md).
- Reviewers aim to respond within two business days. Feel free to nudge if your
  pull request has been waiting longer.
