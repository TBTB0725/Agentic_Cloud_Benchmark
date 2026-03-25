# Commands

This file is a practical command checklist for the current ACBench prototype.

## 1. Environment Check

Print backend diagnostics:

```powershell
python -m acbench.cli --doctor
```

This now reports three backend groups:

- `aiopslab`
- `acbench_code`
- `swe_bench_live_native`

Write a readiness report:

```powershell
python -m acbench.cli --write-readiness-report acbench\runs\readiness_report.json
```

The saved report now separates:

- `aiopslab`
- `acbench_code`
- `swe_bench_live_native`

## 2. Safe Local Demo

Run the local demo suite:

```powershell
python -m acbench.cli --run-local-demo acbench\demo_out
```

Outputs:

- `acbench/demo_out/local_suite_eval.json`
- `acbench/demo_out/local_suite_report.md`

## 3. Local Combined Benchmark

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\combined_local_fixture.json --code-patch acbench\patches\local_repo_buggy_fix.diff
```

## 4. API-Backed Code Prototype

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\code_only_local_repo_buggy.json --code-agent-ref acbench.agents.openai_code:OpenAICodePatchAgent --openai-model gpt-4.1-mini
```

## 5. API-Backed Ops Prototype

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.openai_ops:OpenAIOpsAgent --openai-model gpt-4.1-mini --max-steps 1
```

## 6. Real SWE-bench Native Sample

Run the first confirmed successful native sample:

```powershell
python -m acbench.cli --scenario acbench\scenarios\hf_candidates\casey__just-2835.scenario.json
```

Generate a markdown report for that run:

```powershell
python -m acbench.cli ^
  --run-dir acbench\runs\swebench_native_casey__just-2835-20260324-020909-010779 ^
  --write-run-markdown-report acbench\reports\casey__just-2835.md
```

## 7. Real AIOpsLab Live Sample

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.scripted:DetectionYesAIOpsAgent --max-steps 1
```

## 8. Scenario Validation

Validate a scenario:

```powershell
python -m acbench.cli --validate-scenario --scenario <scenario.json>
```

Check readiness:

```powershell
python -m acbench.cli --check-readiness --scenario <scenario.json>
```

## 9. Native SWE-bench Candidate Discovery

List candidate instances from HuggingFace:

```powershell
python -m acbench.cli ^
  --dataset-name SWE-bench-Live/MultiLang ^
  --dataset-split rust ^
  --list-swebench-hf-candidates ^
  --candidate-limit 10
```

Scaffold a native candidate bundle:

```powershell
python -m acbench.cli ^
  --dataset-name SWE-bench-Live/MultiLang ^
  --dataset-split rust ^
  --instance-id casey__just-2835 ^
  --scaffold-native-swebench-hf-bundle acbench\scenarios\hf_candidates
```

Inspect the instance:

```powershell
python -m acbench.cli --inspect-swebench-instance acbench\scenarios\hf_candidates\casey__just-2835.instance.json
```

## 10. Batch Evaluation

Run batch prediction evaluation:

```powershell
python -m acbench.cli ^
  --manifest acbench\manifests\local_suite.json ^
  --predictions acbench\predictions\local_gold.json ^
  --evaluation-output acbench\runs\local_suite_eval.json
```

Write markdown from evaluation JSON:

```powershell
python -m acbench.cli ^
  --evaluation-json acbench\runs\local_suite_eval.json ^
  --write-markdown-report acbench\reports\local_suite_eval.md
```

## 11. Result Files To Inspect

For each run, the main artifacts are:

- `result.json`
- `summary.json`
- `diagnostics.json`

For native upstream runs, rely on those files rather than terminal noise alone.
