# Quickstart

This document is the shortest path from a fresh checkout to a successful ACBench run.

## What ACBench Is

ACBench is a benchmark prototype that can evaluate:

- code-repair ability
- ops / incident-detection ability
- unified result reporting across both task families

The current prototype already supports two API-backed benchmark paths:

- OpenAI-backed code repair on a local buggy repository
- OpenAI-backed ops detection on a live `AIOpsLab` scenario

## What You Need

Minimum:

- Python 3.11
- the Python dependencies for `acbench/`

For the code prototype:

- `OPENAI_API_KEY`

For the live ops prototype:

- `OPENAI_API_KEY`
- `kubectl`
- `helm`
- a reachable Kubernetes cluster
- the sibling `AIOpsLab/` checkout, if you want to run the live upstream bridge

Use this first:

```powershell
python -m acbench.cli --doctor
```

The doctor output separates three backend groups:

- `acbench_code` for the internal repository-backed code backend
- `swe_bench_live_native` for the native upstream SWE-bench-Live path
- `aiopslab` for the live ops path

If you want a saved readiness report:

```powershell
python -m acbench.cli --write-readiness-report acbench\runs\readiness_report.json
```

## Fastest Safe Run

Run the local demo suite:

```powershell
python -m acbench.cli --run-local-demo acbench\demo_out
```

This is the safest first command because it does not depend on live upstream systems.

## API-Backed Code Prototype

This is the smallest end-to-end autonomous code benchmark:

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\code_only_local_repo_buggy.json --code-agent-ref acbench.agents.openai_code:OpenAICodePatchAgent --openai-model gpt-4.1-mini
```

What happens:

1. ACBench loads a buggy local repository fixture.
2. The OpenAI-backed code agent generates a patch.
3. ACBench applies the patch.
4. ACBench runs build and test commands.
5. ACBench writes normalized benchmark results.

Expected outputs under `acbench/runs/<run_id>/`:

- `result.json`
- `summary.json`
- `diagnostics.json`
- `openai_prompt.txt`
- `openai_response.txt`
- `openai_generated_patch.diff`

## API-Backed Ops Prototype

This is the smallest end-to-end autonomous ops benchmark:

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.openai_ops:OpenAIOpsAgent --openai-model gpt-4.1-mini --max-steps 1
```

What happens:

1. ACBench provisions the live `AIOpsLab` astronomy-shop scenario.
2. The benchmark injects a fault.
3. The OpenAI-backed ops agent receives the problem statement and observation.
4. The agent submits a detection answer.
5. ACBench normalizes the upstream result and writes benchmark outputs.

Expected outputs under `acbench/runs/<run_id>/`:

- `result.json`
- `summary.json`
- `diagnostics.json`
- `aiops_agent_prompt.txt`
- `aiops_agent_response.txt`
- `aiops_agent_action.txt`
- `ops_eval/ops_outcome.json`
- `ops_eval/ops_trace.json`

## Local Combined Benchmark

Use this when you want one safe benchmark that includes both code and ops behavior:

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\combined_local_fixture.json --code-patch acbench\patches\local_repo_buggy_fix.diff
```

This path demonstrates:

- synthetic ops handling
- local code repair
- unified result bundles

## Real Live Samples

Use these after the local paths are working.

### Real AIOpsLab live sample

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.scripted:DetectionYesAIOpsAgent --max-steps 1
```

### Real SWE-bench native sample

```powershell
python -m acbench.cli --scenario acbench\scenarios\hf_candidates\casey__just-2835.scenario.json
```

## How To Read Success

Always judge a run from the saved run bundle, not from terminal noise alone.

For code runs, look for:

- `status = success`
- `code_result.success = true`
- `build_success = true`
- `test_success = true`

For ops runs, look for:

- `status = success`
- `ops_result.success = true`
- `Detection Accuracy = Correct`

The main run files are:

- `result.json`
- `summary.json`
- `diagnostics.json`

For native upstream runs, trust those saved files more than terminal patch noise.

## Recommended Onboarding Order

Use this order for a teammate who knows nothing about the repository:

1. `python -m acbench.cli --doctor`
2. `python -m acbench.cli --run-local-demo acbench\demo_out`
3. Run the API-backed code prototype
4. Run the API-backed ops prototype
5. Run the local combined benchmark
6. Run the real live samples if the upstream bridges are installed
7. Read [SCENARIO_AUTHORING.md](/C:/Projects/ACBench/acbench/docs/SCENARIO_AUTHORING.md) to add new scenarios
8. Read [ARCHITECTURE.md](/C:/Projects/ACBench/acbench/docs/ARCHITECTURE.md) to extend agents or backends

## Next Documents

- [README.md](/C:/Projects/ACBench/acbench/README.md): repository overview
- [COMMANDS.md](/C:/Projects/ACBench/acbench/docs/COMMANDS.md): command reference
- [ENVIRONMENT.md](/C:/Projects/ACBench/acbench/docs/ENVIRONMENT.md): environment expectations
- [SCENARIO_AUTHORING.md](/C:/Projects/ACBench/acbench/docs/SCENARIO_AUTHORING.md): adding new scenarios
- [ARCHITECTURE.md](/C:/Projects/ACBench/acbench/docs/ARCHITECTURE.md): structure and extension points
