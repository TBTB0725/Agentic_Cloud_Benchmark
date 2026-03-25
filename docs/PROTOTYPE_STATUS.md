# Prototype Status

This document summarizes the current ACBench prototype state.

## Goal

The first prototype aims to provide one unified benchmark layer that can run:

- `AIOpsLab`-style live ops tasks
- `SWE-bench-Live`-style live code repair tasks
- local fallback tasks for safe development and demo use

All of these should go through the same ACBench surfaces:

- scenario schema
- runner
- readiness checks
- result format
- summary format
- diagnostics

## Current State

### Working now

- local `code_only` benchmark flow
- local `combined` benchmark flow
- local batch prediction evaluation
- markdown report generation
- API-backed code repair on a local buggy repository
- API-backed ops detection on a live `AIOpsLab` scenario
- real `AIOpsLab` live execution through `acbench`
- real `SWE-bench-Live` native execution through `acbench`
- repository-backed SWE-style code execution through `acbench-code-standalone`

### Verified API-backed prototype paths

#### Code prototype

The OpenAI-backed code prototype has already been executed successfully through:

- `acbench -> local code executor -> OpenAICodePatchAgent -> patch/build/test`

#### Ops prototype

The OpenAI-backed ops prototype has already been executed successfully through:

- `acbench -> aiopslab adapter -> OpenAIOpsAgent -> live detection evaluation`

### Verified real live samples

#### AIOpsLab live

The AIOpsLab live path has already been executed successfully through:

- `acbench -> aiopslab adapter -> upstream orchestrator`

#### SWE-bench-Live native live

The first successful native sample is:

- `acbench/scenarios/hf_candidates/casey__just-2835.scenario.json`

Its successful run artifacts are under:

- `acbench/runs/swebench_native_casey__just-2835-20260324-020909-010779`

Key outputs:

- `result.json`
- `summary.json`
- `diagnostics.json`

Result highlights:

- top-level `status = success`
- `code.backend = swe-bench-live-native`
- `code.success = true`
- `code.resolved = true`
- `pass_to_pass_failure_count = 0`
- `fail_to_pass_failure_count = 0`

## Important Interpretation Note

For native `SWE-bench-Live` runs, terminal output may include upstream messages like:

- `PATCH FAILED TO APPLY CLEANLY`

That output alone does **not** mean the ACBench run failed.

The source of truth is always the run bundle under `acbench/runs/<run_id>/`, especially:

- `result.json`
- `summary.json`

If upstream retries or applies multiple patches internally, the terminal can look noisy even when the final normalized benchmark result is successful.

## Current Gaps

The first prototype goal is already met.

The remaining work is now follow-on engineering rather than prototype viability work:

1. continue reducing documentation noise
2. add more stable native candidate samples
3. strengthen combined benchmark storytelling across ops and code paths
4. continue hardening result/report usability
5. continue replacing upstream runtime dependencies with ACBench-owned backend layers

## Practical Readiness

The prototype is already usable for:

- local benchmark demos
- API-backed code agent scoring
- API-backed ops agent scoring
- real AIOps live runs
- real SWE-bench native runs
- repository-backed SWE-style code runs through `acbench-code-standalone`
- team collaboration on new scenarios

It is not yet the final large benchmark catalog, but it is already a working prototype rather than a paper design.

## Migration Shape

The current migration shape is now:

### Code

- `acbench-code-standalone`
  - repository-backed code tasks owned by ACBench
- `swe-bench-live-native`
  - native upstream instance execution kept for compatibility
- native upstream code probing now lives under:
  - `acbench/backends/code/native_upstream.py`

### Ops

- `aiopslab`
  - still the current live ops executor backend
- native upstream ops probing now lives under:
  - `acbench/backends/ops/native_upstream.py`

This means both backend families now have an internal ACBench layer between the top-level benchmark surfaces and the remaining upstream runtime dependencies.
