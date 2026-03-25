"""Export helpers for bridging ACBench scenarios to external formats."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from acbench.adapters.swebench import SWEBenchCodeExecutor
from acbench.executors.standalone_code import StandaloneCodeExecutor
from acbench.models.runtime import RunConfig
from acbench.runner import ACBenchRunner


def _hf_cache_home() -> Path:
    """Return a writable HuggingFace cache root inside the workspace."""

    cache_root = Path(__file__).resolve().parent / ".hf_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def _infer_swebench_platform(payload: dict[str, Any]) -> str:
    """Infer upstream platform from known instance fields."""

    docker_image = str(payload.get("docker_image", "")).lower()
    if any(token in docker_image for token in ("x86_64", "linux")):
        return "linux"
    if any(token in docker_image for token in ("win", "windows")):
        return "windows"

    platforms = payload.get("platforms", [])
    if isinstance(platforms, list):
        lowered = {str(item).lower() for item in platforms}
        if "linux" in lowered:
            return "linux"
        if "windows" in lowered:
            return "windows"
    return "windows"


def export_swebench_instance(
    scenario_path: str | Path,
    output_path: str | Path,
    use_gold_patch: bool = True,
) -> dict[str, Any]:
    """Export one ACBench scenario into a SWE-bench-style instance payload."""

    runner = ACBenchRunner()
    scenario_file = Path(scenario_path)
    scenario = runner.load_scenario(scenario_file)
    patch_path = scenario.gold_patch_path if use_gold_patch else ""

    run_result = runner.run(
        scenario_path=scenario_file,
        dry_run=False,
        run_config=RunConfig(
            dry_run=False,
            code_patch_path=patch_path,
            max_steps=10,
        ),
    )
    code_result = run_result.code_result
    if code_result is None:
        raise ValueError(f"Scenario {scenario.scenario_id} does not contain a code task.")

    run_config = RunConfig(
        dry_run=False,
        code_patch_path=patch_path,
        max_steps=10,
    )
    native_instance = (
        scenario.code_fault is not None
        and scenario.code_fault.source == "swe-bench-live"
        and bool(scenario.code_fault.instance_path)
    )
    if native_instance:
        instance = SWEBenchCodeExecutor.build_instance_payload(
            scenario,
            run_config,
        )
    else:
        instance = StandaloneCodeExecutor.build_instance_payload(
            scenario,
            run_config,
        )
    instance["PASS_TO_PASS"] = list(code_result.pass_to_pass_success)
    instance["FAIL_TO_PASS"] = list(code_result.fail_to_pass_success)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(instance, indent=2), encoding="utf-8")
    return instance


def extract_swebench_jsonl_instance(
    dataset_path: str | Path,
    instance_id: str,
    output_path: str | Path,
) -> dict[str, Any]:
    """Extract one SWE-bench-Live instance record from a local JSONL dataset."""

    dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset file does not exist: {dataset_file}")

    found: dict[str, Any] | None = None
    with dataset_file.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("instance_id") == instance_id:
                found = record
                break

    if found is None:
        raise ValueError(
            f"Instance `{instance_id}` not found in dataset file: {dataset_file}"
        )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(found, indent=2), encoding="utf-8")
    return found


def create_native_swebench_scenario(
    instance_path: str | Path,
    output_path: str | Path,
    *,
    scenario_id: str = "",
    title: str = "",
    platform: str = "",
) -> dict[str, Any]:
    """Create an ACBench native SWE-bench-Live scenario from an instance JSON file."""

    instance_file = Path(instance_path)
    if not instance_file.exists():
        raise FileNotFoundError(f"Instance file does not exist: {instance_file}")

    instance = json.loads(instance_file.read_text(encoding="utf-8"))
    resolved_id = scenario_id or f"swebench_native_{instance['instance_id']}"
    repo_name = str(instance.get("repo", "unknown/unknown")).split("/")[-1]
    resolved_title = title or f"Native SWE-bench-Live benchmark for {instance['instance_id']}"
    resolved_platform = platform or _infer_swebench_platform(instance)

    scenario = {
        "scenario_id": resolved_id,
        "title": resolved_title,
        "mode": "code_only",
        "service": {
            "application": "swe-bench-live",
            "service": repo_name,
            "deployment": "container",
        },
        "code_fault": {
            "source": "swe-bench-live",
            "defect_id": instance.get("instance_id", resolved_id),
            "description": f"Native SWE-bench-Live instance from {instance.get('repo', 'unknown repo')}.",
            "instance_path": str(instance_file),
            "platform": resolved_platform,
        },
        "success_criteria": {
            "require_repair": True,
            "require_test_success": True,
        },
        "metrics": ["resolved"],
        "tags": [
            "prototype",
            "code",
            "swebench-live",
            "native",
        ],
        "notes": "Generated from a native SWE-bench-Live instance JSON.",
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    return scenario


def scaffold_native_swebench_bundle(
    dataset_path: str | Path,
    instance_id: str,
    output_dir: str | Path,
) -> dict[str, str]:
    """Create both instance JSON and scenario JSON for one native SWE-bench-Live task."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    instance_output = target_dir / f"{instance_id}.instance.json"
    scenario_output = target_dir / f"{instance_id}.scenario.json"

    extract_swebench_jsonl_instance(
        dataset_path=dataset_path,
        instance_id=instance_id,
        output_path=instance_output,
    )
    create_native_swebench_scenario(
        instance_path=instance_output,
        output_path=scenario_output,
    )
    return {
        "instance_path": str(instance_output),
        "scenario_path": str(scenario_output),
    }


def extract_swebench_hf_instance(
    dataset_name: str,
    instance_id: str,
    output_path: str | Path,
    split: str = "",
) -> dict[str, Any]:
    """Extract one SWE-bench-Live instance record from a HuggingFace dataset."""

    cache_root = _hf_cache_home()
    os.environ["HF_HOME"] = str(cache_root)
    os.environ["HF_HUB_CACHE"] = str(cache_root / "hub")
    os.environ["HF_DATASETS_CACHE"] = str(cache_root / "datasets")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    from datasets import load_dataset

    found: dict[str, Any] | None = None
    searched_splits: list[str] = []
    if split:
        dataset_split = load_dataset(dataset_name, split=split, cache_dir=str(cache_root))
        searched_splits.append(split)
        for row in dataset_split:
            if row.get("instance_id") == instance_id:
                found = dict(row)
                break
    else:
        dataset = load_dataset(dataset_name, cache_dir=str(cache_root))
        for split_name in dataset.keys():
            searched_splits.append(split_name)
            for row in dataset[split_name]:
                if row.get("instance_id") == instance_id:
                    found = dict(row)
                    break
            if found is not None:
                break

    if found is None:
        raise ValueError(
            f"Instance `{instance_id}` not found in dataset `{dataset_name}` across splits: {', '.join(searched_splits)}"
        )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(found, indent=2), encoding="utf-8")
    return found


def scaffold_native_swebench_hf_bundle(
    dataset_name: str,
    instance_id: str,
    output_dir: str | Path,
    split: str = "",
) -> dict[str, str]:
    """Create both instance.json and scenario.json for one HF-hosted native SWE-bench-Live task."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    instance_output = target_dir / f"{instance_id}.instance.json"
    scenario_output = target_dir / f"{instance_id}.scenario.json"

    extract_swebench_hf_instance(
        dataset_name=dataset_name,
        instance_id=instance_id,
        output_path=instance_output,
        split=split,
    )
    create_native_swebench_scenario(
        instance_path=instance_output,
        output_path=scenario_output,
    )
    return {
        "instance_path": str(instance_output),
        "scenario_path": str(scenario_output),
    }


def list_swebench_hf_candidates(
    dataset_name: str,
    *,
    split: str = "",
    limit: int = 20,
    require_docker_image: bool = True,
) -> list[dict[str, Any]]:
    """List native SWE-bench-Live candidate instances with completeness diagnostics."""

    cache_root = _hf_cache_home()
    os.environ["HF_HOME"] = str(cache_root)
    os.environ["HF_HUB_CACHE"] = str(cache_root / "hub")
    os.environ["HF_DATASETS_CACHE"] = str(cache_root / "datasets")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    from datasets import load_dataset

    candidates: list[dict[str, Any]] = []

    def _inspect_row(row: dict[str, Any], split_name: str) -> dict[str, Any]:
        payload = dict(row)
        missing_fields = [
            field_name
            for field_name in SWEBenchCodeExecutor.REQUIRED_NATIVE_INSTANCE_FIELDS
            if field_name not in payload
        ]
        has_docker_image = bool(payload.get("docker_image"))
        return {
            "instance_id": payload.get("instance_id", ""),
            "repo": payload.get("repo", ""),
            "split": split_name,
            "version": payload.get("version", ""),
            "base_commit": payload.get("base_commit", ""),
            "has_docker_image": has_docker_image,
            "platform_hint": _infer_swebench_platform(payload),
            "missing_fields": missing_fields,
            "ready": not missing_fields and (has_docker_image or not require_docker_image),
        }

    if split:
        dataset_split = load_dataset(dataset_name, split=split, cache_dir=str(cache_root))
        for row in dataset_split:
            info = _inspect_row(row, split)
            if require_docker_image and not info["has_docker_image"]:
                continue
            candidates.append(info)
            if len(candidates) >= limit:
                break
    else:
        dataset = load_dataset(dataset_name, cache_dir=str(cache_root))
        for split_name in dataset.keys():
            for row in dataset[split_name]:
                info = _inspect_row(row, split_name)
                if require_docker_image and not info["has_docker_image"]:
                    continue
                candidates.append(info)
                if len(candidates) >= limit:
                    return candidates

    return candidates
