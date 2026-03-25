# Architecture

This document explains how the ACBench prototype is organized and where to extend it.

## Top-Level Shape

`acbench/` is the prototype repository root. The important directories are:

- `agents/`: API-backed and scripted benchmark agents
- `adapters/`: live upstream bridges for `AIOpsLab` and `SWE-bench-Live`
- `backends/`: internal runtime, engine, and runner layers for code and ops
- `executors/`: concrete executors selected by the benchmark runner
- `fixtures/`: local repositories and placeholder service assets
- `models/`: scenario and result models
- `patches/`: reference local patches
- `scenarios/`: runnable benchmark scenario definitions
- `scripts/`: repository maintenance utilities
- `tests/`: regression tests
- `docs/`: onboarding, environment, and extension documentation

## Main Execution Flow

Most runs go through this path:

1. `cli.py`
2. `runner.py`
3. scenario validation and readiness checks
4. executor selection
5. normalized result writing

The runner always writes a run bundle under `acbench/runs/<run_id>/`.

## Code Path

There are two code backends.

### `acbench-code-standalone`

This is the internal repository-backed code path.

Relevant files:

- `executors/standalone_code.py`
- `executors/local_code.py`
- `backends/code/runtime.py`
- `backends/code/runner.py`
- `backends/code/standalone.py`

Use this path for:

- local buggy repository fixtures
- API-backed code repair experiments
- stable demos and regression tests

### `swe-bench-live-native`

This is the native upstream bridge for full SWE-bench-Live instances.

Relevant files:

- `adapters/swebench.py`
- `backends/code/native_upstream.py`

Use this path for:

- native instance JSON scenarios
- upstream-compatible live code benchmarking

## Ops Path

There are also two ops layers.

### Internal local ops path

Relevant files:

- `executors/local_ops.py`
- `backends/ops/runtime.py`
- `backends/ops/engine.py`
- `backends/ops/runner.py`

Use this path for:

- local synthetic ops behavior
- combined local scenarios
- future standalone ops backend work

### `aiopslab` live bridge

Relevant files:

- `adapters/aiopslab.py`
- `backends/ops/native_upstream.py`

Use this path for:

- real live `AIOpsLab` scenarios
- Kubernetes-backed ops benchmarking

## Agent Extension Points

### Code agents

Current example:

- `agents/openai_code.py`

Expected behavior:

- inspect the scenario and relevant files
- generate a unified diff patch
- return a patch path that ACBench can apply

### Ops agents

Current examples:

- `agents/openai_ops.py`
- `agents/scripted.py`

Expected behavior:

- optionally implement `configure(run_config)`
- implement `init_context(problem_desc, instructions, apis)`
- implement `async get_action(input_text)`

For live `AIOpsLab` compatibility, return legal actions such as:

- `submit("Yes")`
- `submit("No")`

## How To Add A New Scenario

Start with:

- [SCENARIO_AUTHORING.md](/C:/Projects/ACBench/acbench/docs/SCENARIO_AUTHORING.md)

In practice:

- for code work, copy an example from `scenarios/examples/`
- for native SWE-bench work, scaffold from the CLI
- for live ops work, start from an existing `AIOpsLab`-backed example

## How To Add A New Backend Feature

Recommended order:

1. add or update runtime models under `backends/<domain>/runtime.py`
2. add or update execution logic under `backends/<domain>/engine.py` or `runner.py`
3. update the corresponding executor or adapter
4. add tests under `tests/`
5. update `README.md` and the relevant guide

## How To Keep The Repository Clean

Generated artifacts should not be committed.

Use:

```powershell
powershell -ExecutionPolicy Bypass -File acbench\scripts\cleanup_generated.ps1
```

Generated directories are already ignored through `acbench/.gitignore`.
