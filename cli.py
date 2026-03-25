"""Command-line entrypoint for the ACBench prototype."""

from __future__ import annotations

import argparse
import json

from pathlib import Path

from acbench.adapters.swebench import SWEBenchCodeExecutor
from acbench.backends.ops.native_upstream import inspect_native_environment as inspect_aiopslab_native_environment
from acbench.doctor import (
    build_readiness_bundle,
    inspect_acbench_code_backend,
    inspect_aiopslab,
    inspect_swebench_live,
)
from acbench.demo import run_local_demo
from acbench.evaluate import evaluate_predictions
from acbench.export import (
    create_native_swebench_scenario,
    export_swebench_instance,
    extract_swebench_hf_instance,
    extract_swebench_jsonl_instance,
    list_swebench_hf_candidates,
    scaffold_native_swebench_bundle,
    scaffold_native_swebench_hf_bundle,
)
from acbench.external import aiopslab_root, swebench_live_root
from acbench.models.runtime import RunConfig
from acbench.report import write_markdown_report_from_json, write_run_markdown_report
from acbench.runner import ACBenchRunner
from acbench.validate import check_scenario_readiness


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(description="Run an ACBench prototype scenario.")
    parser.add_argument(
        "--scenario",
        help="Path to a scenario JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use safe dry-run executors instead of live backends.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum steps reserved for future live backends.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Print backend preflight diagnostics and exit.",
    )
    parser.add_argument(
        "--validate-scenario",
        action="store_true",
        help="Validate and print the normalized scenario without executing it.",
    )
    parser.add_argument(
        "--check-readiness",
        action="store_true",
        help="Check whether the scenario is runnable in the current environment.",
    )
    parser.add_argument(
        "--aiops-agent-ref",
        default="",
        help="Live AIOps agent class in `module:Class` format.",
    )
    parser.add_argument(
        "--code-agent-ref",
        default="",
        help="Live code agent class in `module:Class` format.",
    )
    parser.add_argument(
        "--code-patch",
        default="",
        help="Optional patch file to apply for local code execution.",
    )
    parser.add_argument(
        "--openai-model",
        default="",
        help="OpenAI model name used by API-backed benchmark agents.",
    )
    parser.add_argument(
        "--openai-api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable name that stores the OpenAI API key.",
    )
    parser.add_argument(
        "--openai-base-url",
        default="",
        help="Optional OpenAI-compatible base URL for custom providers.",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Path to a manifest JSON for batch prediction evaluation.",
    )
    parser.add_argument(
        "--predictions",
        default="",
        help="Path to a predictions JSON file for batch evaluation.",
    )
    parser.add_argument(
        "--evaluation-output",
        default="",
        help="Where to write batch evaluation output JSON.",
    )
    parser.add_argument(
        "--export-swebench-instance",
        default="",
        help="Write a SWE-bench-style instance JSON for the given scenario.",
    )
    parser.add_argument(
        "--extract-swebench-jsonl-instance",
        default="",
        help="Write one instance record extracted from a local SWE-bench-Live JSONL dataset.",
    )
    parser.add_argument(
        "--dataset-jsonl",
        default="",
        help="Local JSONL dataset path used with --extract-swebench-jsonl-instance.",
    )
    parser.add_argument(
        "--instance-id",
        default="",
        help="Instance ID used with --extract-swebench-jsonl-instance.",
    )
    parser.add_argument(
        "--dataset-name",
        default="",
        help="HuggingFace dataset name used with SWE-bench-Live HF extraction helpers.",
    )
    parser.add_argument(
        "--dataset-split",
        default="",
        help="Optional dataset split used with SWE-bench-Live HF extraction helpers.",
    )
    parser.add_argument(
        "--extract-swebench-hf-instance",
        default="",
        help="Write one instance record extracted from a HuggingFace SWE-bench-Live dataset.",
    )
    parser.add_argument(
        "--inspect-swebench-instance",
        default="",
        help="Inspect one native SWE-bench-Live instance JSON file and print completeness diagnostics.",
    )
    parser.add_argument(
        "--generate-native-swebench-scenario",
        default="",
        help="Write an ACBench native SWE-bench-Live scenario JSON from an instance JSON file.",
    )
    parser.add_argument(
        "--instance-json",
        default="",
        help="Instance JSON path used with --generate-native-swebench-scenario.",
    )
    parser.add_argument(
        "--scaffold-native-swebench-bundle",
        default="",
        help="Create both instance.json and scenario.json from a local SWE-bench-Live JSONL dataset into the given directory.",
    )
    parser.add_argument(
        "--scaffold-native-swebench-hf-bundle",
        default="",
        help="Create both instance.json and scenario.json from a HuggingFace SWE-bench-Live dataset into the given directory.",
    )
    parser.add_argument(
        "--list-swebench-hf-candidates",
        action="store_true",
        help="List candidate native SWE-bench-Live instances from a HuggingFace dataset.",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=20,
        help="Maximum number of native SWE-bench-Live candidates to list.",
    )
    parser.add_argument(
        "--write-readiness-report",
        default="",
        help="Write a combined backend readiness report JSON and exit.",
    )
    parser.add_argument(
        "--write-markdown-report",
        default="",
        help="Write a markdown report from an evaluation JSON file.",
    )
    parser.add_argument(
        "--evaluation-json",
        default="",
        help="Evaluation JSON input used with --write-markdown-report.",
    )
    parser.add_argument(
        "--write-run-markdown-report",
        default="",
        help="Write a markdown report from one benchmark run directory.",
    )
    parser.add_argument(
        "--run-dir",
        default="",
        help="Run directory used with --write-run-markdown-report.",
    )
    parser.add_argument(
        "--run-local-demo",
        default="",
        help="Run the local gold suite demo and write outputs into the given directory.",
    )
    return parser


def run_doctor() -> int:
    """Print backend diagnostics."""

    aiops = inspect_aiopslab_native_environment()
    swe = SWEBenchCodeExecutor.preflight()
    aiops_report = inspect_aiopslab(Path(aiops.repo_root))
    swe_report = inspect_swebench_live(Path(swe.repo_root))
    acbench_code_report = inspect_acbench_code_backend()
    print(
        json.dumps(
            {
                "aiopslab": {
                    **aiops_report.to_dict(),
                    "registry_path": aiops.registry_path,
                    "problem_count": aiops.problem_count,
                    "missing_dependency": aiops.missing_dependency,
                },
                "acbench_code": {
                    **acbench_code_report.to_dict(),
                },
                "swe_bench_live_native": {
                    **swe_report.to_dict(),
                    "launch_root": swe.launch_root,
                    "evaluation_root": swe.evaluation_root,
                    "missing_dependency": swe.missing_dependency,
                },
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    if args.doctor:
        return run_doctor()
    if args.run_local_demo:
        bundle = run_local_demo(args.run_local_demo)
        print(json.dumps(bundle, indent=2))
        return 0
    if args.write_markdown_report:
        if not args.evaluation_json:
            parser.error("--evaluation-json is required with --write-markdown-report")
        output_path = write_markdown_report_from_json(
            evaluation_json_path=args.evaluation_json,
            output_path=args.write_markdown_report,
        )
        print(str(output_path))
        return 0
    if args.write_run_markdown_report:
        if not args.run_dir:
            parser.error("--run-dir is required with --write-run-markdown-report")
        output_path = write_run_markdown_report(
            run_dir=args.run_dir,
            output_path=args.write_run_markdown_report,
        )
        print(str(output_path))
        return 0
    if args.write_readiness_report:
        bundle = build_readiness_bundle(
            aiopslab_root=aiopslab_root(),
            swebench_root=swebench_live_root(),
        )
        output_path = Path(args.write_readiness_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        print(json.dumps(bundle, indent=2))
        return 0
    if args.export_swebench_instance:
        if not args.scenario:
            parser.error("--scenario is required with --export-swebench-instance")
        instance = export_swebench_instance(
            scenario_path=args.scenario,
            output_path=args.export_swebench_instance,
        )
        print(json.dumps(instance, indent=2))
        return 0
    if args.extract_swebench_jsonl_instance:
        if not (args.dataset_jsonl and args.instance_id):
            parser.error(
                "--dataset-jsonl and --instance-id are required with --extract-swebench-jsonl-instance"
            )
        instance = extract_swebench_jsonl_instance(
            dataset_path=args.dataset_jsonl,
            instance_id=args.instance_id,
            output_path=args.extract_swebench_jsonl_instance,
        )
        print(json.dumps(instance, indent=2))
        return 0
    if args.extract_swebench_hf_instance:
        if not (args.dataset_name and args.instance_id):
            parser.error(
                "--dataset-name and --instance-id are required with --extract-swebench-hf-instance"
            )
        instance = extract_swebench_hf_instance(
            dataset_name=args.dataset_name,
            instance_id=args.instance_id,
            output_path=args.extract_swebench_hf_instance,
            split=args.dataset_split,
        )
        print(json.dumps(instance, indent=2))
        return 0
    if args.inspect_swebench_instance:
        info = SWEBenchCodeExecutor.inspect_native_instance_file(args.inspect_swebench_instance)
        print(json.dumps(info, indent=2))
        return 0
    if args.generate_native_swebench_scenario:
        if not args.instance_json:
            parser.error("--instance-json is required with --generate-native-swebench-scenario")
        scenario = create_native_swebench_scenario(
            instance_path=args.instance_json,
            output_path=args.generate_native_swebench_scenario,
        )
        print(json.dumps(scenario, indent=2))
        return 0
    if args.scaffold_native_swebench_bundle:
        if not (args.dataset_jsonl and args.instance_id):
            parser.error(
                "--dataset-jsonl and --instance-id are required with --scaffold-native-swebench-bundle"
            )
        bundle = scaffold_native_swebench_bundle(
            dataset_path=args.dataset_jsonl,
            instance_id=args.instance_id,
            output_dir=args.scaffold_native_swebench_bundle,
        )
        print(json.dumps(bundle, indent=2))
        return 0
    if args.scaffold_native_swebench_hf_bundle:
        if not (args.dataset_name and args.instance_id):
            parser.error(
                "--dataset-name and --instance-id are required with --scaffold-native-swebench-hf-bundle"
            )
        bundle = scaffold_native_swebench_hf_bundle(
            dataset_name=args.dataset_name,
            instance_id=args.instance_id,
            output_dir=args.scaffold_native_swebench_hf_bundle,
            split=args.dataset_split,
        )
        print(json.dumps(bundle, indent=2))
        return 0
    if args.list_swebench_hf_candidates:
        if not args.dataset_name:
            parser.error("--dataset-name is required with --list-swebench-hf-candidates")
        candidates = list_swebench_hf_candidates(
            dataset_name=args.dataset_name,
            split=args.dataset_split,
            limit=args.candidate_limit,
        )
        print(json.dumps(candidates, indent=2))
        return 0
    if args.manifest or args.predictions or args.evaluation_output:
        if not (args.manifest and args.predictions and args.evaluation_output):
            parser.error("--manifest, --predictions, and --evaluation-output must be provided together")
        results = evaluate_predictions(
            manifest_path=args.manifest,
            predictions_path=args.predictions,
            output_path=args.evaluation_output,
        )
        print(json.dumps(results, indent=2))
        return 0
    if not args.scenario:
        parser.error("--scenario is required unless --doctor is used")
    runner = ACBenchRunner()
    if args.validate_scenario:
        scenario = runner.load_scenario(args.scenario)
        print(json.dumps(scenario.to_dict(), indent=2))
        return 0
    if args.check_readiness:
        scenario = runner.load_scenario(args.scenario)
        report = check_scenario_readiness(scenario)
        print(json.dumps(report.to_dict(), indent=2))
        return 0
    run_config = RunConfig(
        dry_run=args.dry_run,
        max_steps=args.max_steps,
        aiops_agent_ref=args.aiops_agent_ref,
        code_agent_ref=args.code_agent_ref,
        code_patch_path=args.code_patch,
        openai_model=args.openai_model,
        openai_api_key_env=args.openai_api_key_env,
        openai_base_url=args.openai_base_url,
        aiops_agent_type=args.aiops_agent_ref or "unconfigured",
        code_agent_type=args.code_agent_ref or "unconfigured",
    )
    result = runner.run(args.scenario, dry_run=args.dry_run, run_config=run_config)
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
