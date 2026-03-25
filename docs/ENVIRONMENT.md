# Environment

This document describes the current environment expectations for the ACBench prototype.

## Current Reality

The prototype already has:

- stable local fallback paths
- a working real `AIOpsLab` live path
- a working real `SWE-bench-Live` native path
- a working internal repository-backed code path under `acbench-code-standalone`
- internal native-upstream probing layers for both code and ops backends

So this document is no longer a list of future requirements only. It is a reference for keeping those paths healthy and reproducible.

## Core Checks

Use:

```powershell
python -m acbench.cli --doctor
```

Or save a full readiness report:

```powershell
python -m acbench.cli --write-readiness-report acbench\runs\readiness_report.json
```

The readiness bundle now separates:

- `aiopslab`
- `acbench_code`
- `swe_bench_live_native`

## AIOpsLab Live Requirements

The `AIOpsLab` live path depends on:

- Python modules required by the upstream repo
- `kubectl`
- `helm`
- a reachable Kubernetes context
- the local AIOpsLab checkout and config

The current live executor still reports backend name:

- `aiopslab`

But environment probing for this path is now isolated under:

- `acbench/backends/ops/native_upstream.py`

Useful command:

```powershell
python -m acbench.cli --check-readiness --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json
```

Known good live command:

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.scripted:DetectionYesAIOpsAgent --max-steps 1
```

## SWE-bench-Live Native Requirements

The native `SWE-bench-Live` path depends on:

- Python modules required by the upstream repo
- Docker daemon availability
- a complete native instance JSON
- a usable upstream docker image for that instance

In diagnostics and normalized results, this path should now appear as:

- `swe-bench-live-native`

Useful command:

```powershell
python -m acbench.cli --check-readiness --scenario acbench\scenarios\hf_candidates\casey__just-2835.scenario.json
```

Known good live command:

```powershell
python -m acbench.cli --scenario acbench\scenarios\hf_candidates\casey__just-2835.scenario.json
```

Important:

- native instance stability is still upstream-instance-dependent
- a structurally valid instance can still drift over time
- final success should be judged from `result.json` and `summary.json`
- native runs should now appear with backend name `swe-bench-live-native`

## Local Fallback Paths

The local fallback paths are the safest way to keep development and demos stable.

### Local code

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\code_only_local_repo_buggy.json
python -m acbench.cli --scenario acbench\scenarios\examples\code_only_local_repo_buggy.json --code-patch acbench\patches\local_repo_buggy_fix.diff
```

### Local combined

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\combined_local_fixture.json --code-patch acbench\patches\local_repo_buggy_fix.diff
```

## Practical Guidance

Use this order when checking a new machine:

1. `--doctor`
2. local demo
3. local combined scenario
4. native SWE-bench sample
5. AIOpsLab live sample

That keeps debugging simple and separates environment issues from benchmark logic issues.
