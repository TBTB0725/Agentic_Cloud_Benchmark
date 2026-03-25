# Demo Guide

This guide is for presenting the current ACBench prototype to teammates or an advisor.

## Recommended Demo Order

Use this order:

1. show environment readiness
2. show the API-backed code prototype
3. show the API-backed ops prototype
4. optionally show a safe local demo
5. optionally show the real upstream bridge paths
6. show generated run reports

## 1. Environment Readiness

```powershell
python -m acbench.cli --doctor
```

Optional saved report:

```powershell
python -m acbench.cli --write-readiness-report acbench\runs\readiness_report.json
```

## 2. API-Backed Code Prototype

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\code_only_local_repo_buggy.json --code-agent-ref acbench.agents.openai_code:OpenAICodePatchAgent --openai-model gpt-4.1-mini
```

Show:

- the buggy local repository fixture
- the generated patch artifact
- the final `result.json` and `summary.json`

## 3. API-Backed Ops Prototype

```powershell
$env:OPENAI_API_KEY="<your-key>"
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.openai_ops:OpenAIOpsAgent --openai-model gpt-4.1-mini --max-steps 1
```

Show:

- the live astronomy-shop fault injection
- the saved agent prompt / response / action files
- the final detection result in `result.json`

## 4. Optional Safe Local Demo

```powershell
python -m acbench.cli --run-local-demo acbench\demo_out
```

Show:

- `acbench/demo_out/local_suite_eval.json`
- `acbench/demo_out/local_suite_report.md`

## 5. Optional Real SWE-bench Native Demo

Use the first confirmed successful sample:

```powershell
python -m acbench.cli --scenario acbench\scenarios\hf_candidates\casey__just-2835.scenario.json
```

Then generate a single-run markdown report:

```powershell
python -m acbench.cli ^
  --run-dir acbench\runs\swebench_native_casey__just-2835-20260324-020909-010779 ^
  --write-run-markdown-report acbench\reports\casey__just-2835.md
```

Important message for the audience:

- upstream terminal logs may look noisy
- benchmark success should be judged from `result.json` and `summary.json`
- ACBench normalizes the final outcome

## 6. Optional Real AIOpsLab Live Demo

```powershell
python -m acbench.cli --scenario acbench\scenarios\examples\ops_only_astronomy_shop.json --aiops-agent-ref acbench.agents.scripted:DetectionYesAIOpsAgent --max-steps 1
```

Use this to show the upstream bridge path without the API-backed prototype agent.

## 7. What To Highlight

When presenting, emphasize:

- one unified benchmark layer
- working API-backed code benchmark
- working API-backed ops benchmark
- optional live upstream bridges
- local fallback for stable development
- standardized outputs

The key artifacts are:

- `result.json`
- `summary.json`
- `diagnostics.json`
- markdown reports

## 8. What Not To Claim

Do not claim yet:

- a full benchmark catalog
- a production leaderboard
- stable success for every upstream SWE-bench instance

The correct claim is:

- the first prototype is working
- both API-backed prototype paths are working
- both live backend families are integrated as optional bridges
- at least one real successful sample exists for each family
