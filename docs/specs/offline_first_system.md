# Offline-First System Specification

## Overview
The offline-first flavour of `tle_fetcher` ensures operators can continue
requesting orbital elements even when remote networks are unreachable.
The system treats every CLI invocation as a workflow that will use
local data until network access is explicitly requested or restored.

The architecture is composed of three vertical slices:

1. **Data Plane** – local caching, snapshot storage, and offline
   synchronisation logic.
2. **Access Plane** – transport adapters that talk to upstream TLE
   services when the workflow allows networking.
3. **Experience Plane** – command-line interfaces and future UI clients
   that orchestrate both planes according to policy.

## Architecture Diagram
```
┌────────────────────────────────────────────────────────────┐
│ Experience Plane                                           │
│   • CLI façade (`tle_fetcher.cli`)                         │
│   • Automation hooks (`--json`, `--quiet`)                 │
├───────────────────────┬────────────────────────────────────┤
│ Access Plane          │ Data Plane                         │
│   • `sources` module  │   • `cache` module                 │
│   • HTTP adapters     │   • snapshot registry              │
│   • credential store  │   • integrity + expiry policies    │
└───────────────────────┴────────────────────────────────────┘
```

## Offline Policies

* **Default mode:** Start in offline mode by consulting the cache.
  Only after cache lookup fails does the resolver request remote data.
* **Cache TTL enforcement:** The cache honours module-configured TTLs;
  expired snapshots are treated as soft failures that can be overridden
  with `--allow-stale` (future flag).
* **Write-through caching:** Successful remote fetches are persisted to
  the cache immediately before returning data to the caller.
* **Credential sandboxing:** Authentication material is only required
  for remote fetches; offline resolutions never depend on them.
* **Deterministic retries:** Network calls use deterministic backoff and
  jitter to avoid stampeding once connectivity returns.

## Module Interfaces

| Module                        | Responsibility                                   | Key Functions |
|-------------------------------|--------------------------------------------------|---------------|
| `tle_fetcher.cli`             | CLI façade orchestrating policies and IO         | `bootstrap_cli(argv)` -> int |
| `tle_fetcher.cli.legacy`      | Legacy implementation with parsing + execution   | `parse_args(argv)` -> Namespace, `run_cli(ns)` -> int |
| `tle_fetcher.sources` *(fut)* | Adapters for CelesTrak, Space-Track, etc.        | `fetch(id, options)` -> `TLE` |
| `tle_fetcher.cache` *(fut)*   | TTL-aware persistence for offline snapshots      | `load(id)` -> Optional[`TLE`], `store(tle)` |
| `tle_fetcher.policy` *(fut)*  | Offline/online decision engine                   | `resolve(request)` -> `ResolutionPlan` |


## CLI Contract

* **Invocation:** `tle-fetcher [options] <NORAD_ID...>` continues to work
  via the legacy shim, while the new package exposes `python -m
  tle_fetcher.cli`.
* **Outputs:** Text output defaults to human-friendly copy; JSON mode
  persists for automation integrations.
* **Exit codes:** `0` success, `2` partial/complete failure, other codes
  reserved for parser or IO errors.
* **Configuration:** Flags for TTL, retry counts, output directory, and
  caching semantics remain stable to ease migration to the modular
  implementation.
