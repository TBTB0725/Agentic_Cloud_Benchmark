# ACBench Prototype

`acbench/` is the standalone fusion layer for the first ACBench prototype.

It unifies:

- `AIOpsLab`-style live ops benchmarking
- `SWE-bench-Live`-style live code benchmarking
- local fallback scenarios for stable development and demos

This is no longer only a skeleton. The prototype now has:

- a unified scenario schema
- a unified runner
- readiness and diagnostics
- normalized `result.json` and `summary.json`
- markdown reporting
- real successful live samples for both backend families
- API-backed code and ops prototype paths
- internal backend layering for both code and ops migration work

## Current Capability

ACBench can currently do all of the following:

- run local `code_only` benchmark scenarios
- run local `combined` benchmark scenarios
- run local batch prediction evaluation
- run an OpenAI-backed code repair benchmark on a local buggy repository
- run an OpenAI-backed ops detection benchmark on a live `AIOpsLab` scenario
- run real `AIOpsLab` live scenarios through the ACBench adapter
- run real `SWE-bench-Live` native scenarios through the ACBench adapter
- run repository-backed SWE-style code tasks through the internal `acbench-code-standalone` path
- call an API-backed code agent to generate a patch for repository-backed code tasks
- call an API-backed ops agent to answer a live detection task
- generate run-level and batch-level markdown reports

## What It Cannot Claim Yet

ACBench should not yet be described as:

- a full benchmark catalog
- a production leaderboard
- a fully mature combined live code+ops benchmark suite
- a guarantee that every upstream SWE-bench instance is stable over time

The correct claim is:

- this is a working first prototype
- both live backend families are integrated
- local fallback paths are stable
- both API-backed prototype paths are working
- at least one successful real live sample exists for each backend family

## Repository Hygiene

Generated outputs should be treated as local artifacts, not source assets.

The `acbench/.gitignore` file now excludes:

- `runs/`
- `out/`
- `demo_out/`
- `reports/`
- `.hf_cache/`
- `__pycache__/`
- `*.pyc`

To remove generated artifacts from a working copy, run:

```powershell
powershell -ExecutionPolicy Bypass -File acbench\scripts\cleanup_generated.ps1
```

## Recommended Starting Points

### Safe local demo

```powershell
python -m acbench.cli --run-local-demo acbench\demo_out
```

### Local combined scenario

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\combined_local_fixture.json --code-patch acbench\patches\local_repo_buggy_fix.diff
```

### API-backed code agent prototype

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\code_only_local_repo_buggy.json --code-agent-ref acbench.agents.openai_code:OpenAICodePatchAgent --openai-model gpt-4.1-mini
```

### Real SWE-bench native sample

```powershell
python -m acbench.cli --scenario acbench\scenarios\hf_candidates\casey__just-2835.scenario.json
```

### Real AIOpsLab live sample

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.scripted:DetectionYesAIOpsAgent --max-steps 1
```

### API-backed ops agent prototype

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.openai_ops:OpenAIOpsAgent --openai-model gpt-4.1-mini --max-steps 1
```

## Key Outputs

Each run should produce a bundle under `acbench/runs/`.

The main files are:

- `result.json`
- `summary.json`
- `diagnostics.json`

For native upstream runs, use those files as the source of truth. Upstream terminal output may contain noisy patch-apply messages even when the final normalized benchmark result is successful.

For code runs, the normalized backend name now distinguishes:

- `acbench-code-standalone`
- `swe-bench-live-native`

`swe-bench-live-native` is reserved for native instance scenarios with `code_fault.instance_path`.

Repository-backed SWE-style code tasks now use a dedicated internal executor instead of flowing through the native upstream adapter path.

For ops runs, the current live backend is still `aiopslab`, but upstream environment probing and registry discovery are now being isolated under `acbench/backends/ops/native_upstream.py`.

## Useful Commands

### Environment and readiness

```powershell
python -m acbench.cli --doctor
python -m acbench.cli --write-readiness-report acbench\runs\readiness_report.json
```

### Scenario validation

```powershell
python -m acbench.cli --validate-scenario --scenario <scenario.json>
python -m acbench.cli --check-readiness --scenario <scenario.json>
```

### Batch evaluation

```powershell
python -m acbench.cli ^
  --manifest acbench\manifests\local_suite.json ^
  --predictions acbench\predictions\local_gold.json ^
  --evaluation-output acbench\runs\local_suite_eval.json
```

### Run-level markdown report

```powershell
python -m acbench.cli ^
  --run-dir acbench\runs\<run_id> ^
  --write-run-markdown-report acbench\reports\<run_id>.md
```

### Batch markdown report

```powershell
python -m acbench.cli ^
  --evaluation-json acbench\runs\local_suite_eval.json ^
  --write-markdown-report acbench\reports\local_suite_eval.md
```

## Native SWE-bench Flow

To discover native candidates from HuggingFace:

```powershell
python -m acbench.cli ^
  --dataset-name SWE-bench-Live/MultiLang ^
  --dataset-split rust ^
  --list-swebench-hf-candidates ^
  --candidate-limit 10
```

To scaffold one native bundle:

```powershell
python -m acbench.cli ^
  --dataset-name SWE-bench-Live/MultiLang ^
  --dataset-split rust ^
  --instance-id casey__just-2835 ^
  --scaffold-native-swebench-hf-bundle acbench\scenarios\hf_candidates
```

## Documentation Map

- `acbench/docs/QUICKSTART.md`
- `acbench/docs/ARCHITECTURE.md`
- `acbench/docs/PROTOTYPE_STATUS.md`
- `acbench/docs/SCENARIO_AUTHORING.md`
- `acbench/docs/STANDALONE_STATUS.md`
- `acbench/docs/DEMO_GUIDE.md`
- `acbench/docs/COMMANDS.md`
- `acbench/docs/ENVIRONMENT.md`

## Layout

- `models/`: scenario and result models
- `agents/`: API-backed and scripted benchmark agents
- `backends/`: internal migration layers for code and ops runtime helpers
- `executors/`: local and dry-run executors
- `adapters/`: AIOpsLab and SWE-bench-Live integrations
- `fixtures/`: local repository and placeholder assets
- `scenarios/`: local examples and native candidate bundles
- `scripts/`: repository maintenance utilities
- `tests/`: regression coverage
- `runner.py`: top-level benchmark orchestration
- `cli.py`: command-line entrypoint
