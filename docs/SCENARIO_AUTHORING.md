# Scenario Authoring

This guide explains how to add new scenarios to the current ACBench prototype.

## Scenario Types

The prototype currently supports three practical scenario shapes:

1. local `code_only`
2. local `combined`
3. native `SWE-bench-Live` code scenarios

`AIOpsLab` live scenarios are also supported, but they should usually reuse known upstream problem IDs first.

## 1. Local Code Scenario

Use this when:

- you want a stable local benchmark
- you want to test patch/build/test flow without upstream containers

Reference:

- `acbench/scenarios/examples/code_only_local_repo_buggy.json`

Important fields:

- `mode: code_only`
- `service.repository_path`
- `code_fault.source: acbench`
- `build.rebuild_cmds`
- `build.test_cmds`
- `gold_patch_path`

## 2. Local Combined Scenario

Use this when:

- you want one benchmark that includes both ops and code
- you want a safe demo path

Reference:

- `acbench/scenarios/examples/combined_local_fixture.json`

Important fields:

- `mode: combined`
- `ops_fault.source: acbench`
- `code_fault.source: acbench`

## 3. Native SWE-bench-Live Scenario

Use this when:

- you want to benchmark against a real upstream SWE-bench-Live instance

There are two common creation paths.

### From HuggingFace

```powershell
python -m acbench.cli ^
  --dataset-name SWE-bench-Live/MultiLang ^
  --dataset-split rust ^
  --instance-id <instance_id> ^
  --scaffold-native-swebench-hf-bundle acbench\scenarios\hf_candidates
```

### From a local JSONL dataset

```powershell
python -m acbench.cli ^
  --dataset-jsonl <dataset.jsonl> ^
  --instance-id <instance_id> ^
  --scaffold-native-swebench-bundle acbench\scenarios\bundles
```

This produces:

- `<instance_id>.instance.json`
- `<instance_id>.scenario.json`

Important fields in the generated scenario:

- `mode: code_only`
- `code_fault.source: swe-bench-live`
- `code_fault.instance_path`
- `code_fault.platform`

## Export Note

`--export-swebench-instance` now follows the current backend split:

- repository-backed scenarios export through the internal `acbench-code-standalone` payload path
- native scenarios export through the native `swe-bench-live-native` payload path

## 4. Validate Before Running

Always run:

```powershell
python -m acbench.cli --validate-scenario --scenario <scenario.json>
python -m acbench.cli --check-readiness --scenario <scenario.json>
```

For native SWE-bench scenarios, readiness checks:

- required instance fields
- docker image presence
- backend import readiness
- docker availability

## 5. Naming Guidance

Use names that make benchmark purpose obvious.

Examples:

- `code_only_local_repo_buggy`
- `combined_local_fixture`
- `swebench_native_casey__just-2835`

## 6. Stability Guidance

Prefer:

- local scenarios for demos and regression tests
- known-good native SWE-bench instances for live code demos
- existing AIOpsLab problems for live ops demos

Avoid:

- adding many live instances before checking readiness
- assuming upstream terminal noise means failure
- using incomplete native instance JSON files

## 7. Current Good References

- local code: `acbench/scenarios/examples/code_only_local_repo_buggy.json`
- local combined: `acbench/scenarios/examples/combined_local_fixture.json`
- native swebench live: `acbench/scenarios/hf_candidates/casey__just-2835.scenario.json`
- live ops example: `acbench/scenarios/examples/ops_only_astronomy_shop.json`
