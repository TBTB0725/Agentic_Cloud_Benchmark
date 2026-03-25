"""Batch patch evaluation utilities for the ACBench prototype."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from acbench.models.runtime import RunConfig
from acbench.runner import ACBenchRunner


def _resolve_patch_input(
    scenario_path: Path,
    payload: dict[str, Any],
) -> str:
    """Resolve patch input from a prediction entry."""

    scenario = ACBenchRunner().load_scenario(scenario_path)
    if payload.get("use_gold_patch"):
        if not scenario.gold_patch_path:
            raise ValueError(
                f"Scenario {scenario.scenario_id} does not define gold_patch_path."
            )
        return scenario.gold_patch_path
    if payload.get("code_patch_path"):
        return str(payload["code_patch_path"])
    if payload.get("model_patch_path"):
        return str(payload["model_patch_path"])
    if payload.get("model_patch"):
        patch_text = str(payload["model_patch"])
        out_dir = Path("acbench") / "temp_patches"
        out_dir.mkdir(parents=True, exist_ok=True)
        temp_path = out_dir / f"{scenario.scenario_id}.diff"
        temp_path.write_text(patch_text, encoding="utf-8")
        return str(temp_path)
    return ""


def evaluate_predictions(
    manifest_path: str | Path,
    predictions_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """Evaluate a prediction bundle against a scenario manifest."""

    manifest_file = Path(manifest_path)
    predictions_file = Path(predictions_path)
    output_file = Path(output_path)

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    predictions = json.loads(predictions_file.read_text(encoding="utf-8"))
    runner = ACBenchRunner()

    results: dict[str, Any] = {
        "manifest": str(manifest_file),
        "predictions": str(predictions_file),
        "submitted": 0,
        "success": 0,
        "failure": 0,
        "missing": [],
        "results": {},
    }

    for entry in manifest["scenarios"]:
        scenario_path = Path(entry["scenario"])
        scenario = runner.load_scenario(scenario_path)
        pred = predictions.get(scenario.scenario_id)
        if pred is None:
            results["missing"].append(scenario.scenario_id)
            continue

        patch_path = _resolve_patch_input(scenario_path, pred)
        run_config = RunConfig(
            dry_run=False,
            code_patch_path=patch_path,
            max_steps=int(pred.get("max_steps", 10)),
        )
        run_result = runner.run(
            scenario_path=scenario_path,
            dry_run=False,
            run_config=run_config,
        )
        code_result = run_result.code_result
        summary = {
            "status": run_result.status,
            "result_path": run_result.artifacts.result_path,
            "summary_path": run_result.artifacts.summary_path,
            "code_backend": code_result.backend if code_result else "",
            "build_success": code_result.build_success if code_result else False,
            "test_success": code_result.test_success if code_result else False,
            "pass_to_pass_success": code_result.pass_to_pass_success if code_result else [],
            "fail_to_pass_success": code_result.fail_to_pass_success if code_result else [],
            "pass_to_pass_failure": code_result.pass_to_pass_failure if code_result else [],
            "fail_to_pass_failure": code_result.fail_to_pass_failure if code_result else [],
        }
        results["results"][scenario.scenario_id] = summary
        results["submitted"] += 1
        if run_result.status == "success":
            results["success"] += 1
        else:
            results["failure"] += 1

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
