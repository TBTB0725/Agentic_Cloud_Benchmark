# Standalone Status

This document summarizes what `acbench/` can already do on its own and what still remains as an upstream compatibility bridge.

## What Works Inside `acbench/`

These capabilities are already owned by `acbench/` itself:

- scenario loading and normalization
- unified runner and result schema
- repository-backed code evaluation via `acbench-code-standalone`
- local synthetic ops evaluation via `acbench-local-ops`
- API-backed code repair on a local buggy repository
- local combined benchmark scenarios
- API-backed agent integration surfaces
- batch evaluation and markdown reporting
- standalone code runtime / engine / runner structure
- standalone ops runtime / engine / runner structure

Practical meaning:

- if you only keep `acbench/`, you still retain the local prototype workflows
- if you only keep `acbench/`, you still retain the API-backed local code prototype
- the local code and local ops paths are no longer conceptually tied to the sibling repositories

## What Still Depends on Upstream Repositories

Two live compatibility bridges still remain:

### `swe-bench-live-native`

Still depends on the sibling SWE-bench-Live checkout for:

- native instance execution
- native import probing
- native environment checks

### `aiopslab`

Still depends on the sibling AIOpsLab checkout for:

- live orchestrator execution
- upstream problem registry
- upstream config and tool layout
- upstream-oriented doctor and readiness assumptions

## What This Means for GitHub Packaging

If you want to publish only `acbench/`:

- the local prototype is already meaningful and runnable
- the API-backed local code prototype is already meaningful and runnable
- the native live bridges should be described as optional compatibility integrations
- generated outputs should not be committed

Recommended exclusions:

- `acbench/runs/`
- `acbench/out/`
- `acbench/demo_out/`
- `acbench/reports/`
- `acbench/.hf_cache/`

## Current Recommended Positioning

Use this wording when describing the repository:

- `acbench/` is the primary prototype codebase
- local code and local ops benchmarking are ACBench-owned capabilities
- the API-backed local code benchmark is ACBench-owned
- native AIOpsLab and SWE-bench-Live support currently remain optional bridge integrations

## Next Migration Targets

The next standalone milestones are:

1. replace native SWE-bench-Live execution with an ACBench-owned native code runtime
2. replace live AIOpsLab execution with an ACBench-owned ops runtime
3. remove remaining sibling-repo assumptions from doctor/readiness and migration docs
