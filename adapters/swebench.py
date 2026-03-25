"""Adapter utilities for integrating SWE-bench-Live into ACBench."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from acbench.backends.code.engine import build_engine_for_instance
from acbench.backends.code.native_upstream import (
    NativeSWEBenchEnvironment,
    inspect_native_environment,
)
from acbench.backends.code.runtime import CodeRunRequest, NativeCodeInstance
from acbench.doctor import inspect_acbench_code_backend
from acbench.executors.base import BenchmarkExecutor
from acbench.models.result import ExecutorResult
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


SWEBenchPreflight = NativeSWEBenchEnvironment


class SWEBenchCodeExecutor(BenchmarkExecutor):
    """Native SWE-bench-Live executor for docker-backed upstream instances only."""

    REQUIRED_NATIVE_INSTANCE_FIELDS = (
        "instance_id",
        "repo",
        "patch",
        "test_patch",
        "PASS_TO_PASS",
        "FAIL_TO_PASS",
        "test_cmds",
    )

    def __init__(self) -> None:
        super().__init__(backend_name="swe-bench-live-native")

    def execute(
        self,
        scenario: ScenarioSpec,
        run_dir: Path,
        run_config: RunConfig,
    ) -> ExecutorResult:
        if (
            scenario.code_fault is None
            or scenario.code_fault.source != "swe-bench-live"
            or not scenario.code_fault.instance_path
        ):
            raise ValueError(
                "SWEBenchCodeExecutor only supports native SWE-bench-Live "
                "scenarios with code_fault.instance_path."
            )
        instance = self.build_instance_payload(scenario, run_config)
        instance_path = run_dir / "swebench_instance.json"
        instance_path.write_text(json.dumps(instance, indent=2), encoding="utf-8")
        prediction_path = run_dir / "swebench_prediction.json"
        prediction_path.write_text(
            json.dumps(self.build_prediction_payload(instance), indent=2),
            encoding="utf-8",
        )

        preflight = self.preflight_for_scenario(scenario)
        if not preflight.import_ready:
            raise RuntimeError(
                "SWE-bench-Live backend is not import-ready in this environment. "
                f"Missing dependency: {preflight.missing_dependency or 'unknown'}. "
                f"Prepared instance payload at {instance_path} and prediction payload at {prediction_path}."
            )

        report = self._run_single_instance(instance, output_dir=run_dir / "swebench_eval")
        result = self.normalize_report(
            report,
            instance,
            backend_name=self.backend_name_for_instance_payload(instance),
        )
        result.logs = {
            "instance_path": str(instance_path),
            "prediction_path": str(prediction_path),
            "report_path": str((run_dir / "swebench_eval" / instance["instance_id"] / "report.json")),
        }
        return result

    @classmethod
    def preflight(cls) -> SWEBenchPreflight:
        """Check native upstream repository availability and import readiness."""

        return inspect_native_environment()

    @classmethod
    def standalone_preflight(cls) -> SWEBenchPreflight:
        """Check readiness for the internal standalone repository-backed code backend."""

        report = inspect_acbench_code_backend()
        return SWEBenchPreflight(
            repo_root=report.repo_root,
            launch_root="",
            evaluation_root="",
            import_ready=True,
            backend_type="standalone-local-code",
            missing_dependency="",
        )

    @classmethod
    def preflight_for_scenario(cls, scenario: ScenarioSpec) -> SWEBenchPreflight:
        """Select the appropriate preflight path for one code scenario."""

        native_swebench_instance = (
            scenario.code_fault is not None
            and scenario.code_fault.source == "swe-bench-live"
            and bool(scenario.code_fault.instance_path)
        )
        if native_swebench_instance:
            return cls.preflight()
        return cls.standalone_preflight()

    @staticmethod
    def build_instance_payload(
        scenario: ScenarioSpec,
        run_config: RunConfig,
    ) -> dict[str, Any]:
        """Load one native SWE-bench-Live instance payload for evaluation."""

        if scenario.code_fault is None:
            raise ValueError(f"Scenario {scenario.scenario_id} does not contain a code fault.")
        if not scenario.code_fault.instance_path:
            raise ValueError(
                "SWEBenchCodeExecutor.build_instance_payload only supports "
                "native scenarios with code_fault.instance_path."
            )
        patch_text = ""
        if run_config.code_patch_path:
            patch_file = Path(run_config.code_patch_path)
            if not patch_file.is_absolute():
                patch_file = Path.cwd() / patch_file
            if patch_file.exists():
                patch_text = patch_file.read_text(encoding="utf-8")

        instance_path = Path(scenario.code_fault.instance_path)
        if not instance_path.is_absolute():
            instance_path = Path.cwd() / instance_path
        instance = json.loads(instance_path.read_text(encoding="utf-8"))
        instance["instance_id"] = instance.get("instance_id", scenario.scenario_id)
        if patch_text:
            instance["pred_patch"] = patch_text
        elif "pred_patch" not in instance:
            instance["pred_patch"] = instance.get("patch", "")
        instance["platform"] = instance.get("platform", scenario.code_fault.platform or "linux")
        instance["PASS_TO_PASS"] = list(instance.get("PASS_TO_PASS", []))
        instance["FAIL_TO_PASS"] = list(instance.get("FAIL_TO_PASS", []))
        instance["rebuild_cmds"] = list(instance.get("rebuild_cmds", []))
        instance["test_cmds"] = list(instance.get("test_cmds", []))
        instance["print_cmds"] = list(instance.get("print_cmds", []))
        instance["test_patch"] = instance.get("test_patch", "")
        instance["log_parser"] = instance.get("log_parser", instance.get("parser", ""))
        return instance

    @classmethod
    def normalize_report(
        cls,
        report: dict[str, Any],
        instance: dict[str, Any],
        backend_name: str | None = None,
    ) -> ExecutorResult:
        """Normalize a SWE-style evaluation report into ACBench format."""

        pass_to_pass = report.get("PASS_TO_PASS", {})
        fail_to_pass = report.get("FAIL_TO_PASS", {})
        pass_to_pass_success = list(pass_to_pass.get("success", instance.get("PASS_TO_PASS", [])))
        pass_to_pass_failure = list(pass_to_pass.get("failure", []))
        fail_to_pass_success = list(fail_to_pass.get("success", instance.get("FAIL_TO_PASS", [])))
        fail_to_pass_failure = list(fail_to_pass.get("failure", []))
        resolved = bool(report.get("resolved", False))
        resolved_backend_name = backend_name or cls.backend_name_for_instance_payload(instance)

        return ExecutorResult(
            backend=resolved_backend_name,
            success=resolved,
            repaired=resolved,
            build_success=resolved,
            test_success=resolved,
            pass_to_pass_success=pass_to_pass_success,
            pass_to_pass_failure=pass_to_pass_failure,
            fail_to_pass_success=fail_to_pass_success,
            fail_to_pass_failure=fail_to_pass_failure,
            metrics={
                "submitted_instance_id": report.get("instance_id", instance.get("instance_id", "")),
                "resolved": resolved,
            },
            details={
                "raw_report": report,
                "instance_payload": instance,
            },
        )

    @staticmethod
    def backend_name_for_instance_payload(instance: dict[str, Any]) -> str:
        """Return the normalized backend name for native SWE-bench-Live execution."""

        return "swe-bench-live-native"

    @staticmethod
    def build_prediction_payload(instance: dict[str, Any]) -> dict[str, Any]:
        """Build a SWE-bench-style predictions JSON payload for one instance."""

        return {
            instance["instance_id"]: {
                "model_patch": instance.get("pred_patch", ""),
            }
        }

    @classmethod
    def _run_single_instance(cls, instance: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        """Run one SWE-style instance through the current ACBench code engine."""

        runtime_instance = NativeCodeInstance.from_payload(instance)
        outcome = build_engine_for_instance(runtime_instance).run(
            CodeRunRequest(
                instance=runtime_instance,
                output_dir=output_dir,
                keep_workspace=True,
            )
        )
        report = outcome.to_report(runtime_instance.instance_id)
        report.update(
            {
                "instance_id": runtime_instance.instance_id,
                "resolved": outcome.resolved,
            }
        )
        return report

    @classmethod
    def inspect_native_instance_file(cls, instance_path: str | Path) -> dict[str, Any]:
        """Inspect one native SWE-bench-Live instance JSON file for required fields."""

        resolved = Path(instance_path)
        if not resolved.is_absolute():
            resolved = Path.cwd() / resolved
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        missing_fields = [
            field_name
            for field_name in cls.REQUIRED_NATIVE_INSTANCE_FIELDS
            if field_name not in payload
        ]
        return {
            "instance_path": str(resolved),
            "instance_id": payload.get("instance_id", ""),
            "missing_fields": missing_fields,
            "has_docker_image": bool(payload.get("docker_image")),
            "platform_hint": cls._infer_platform_hint(payload),
        }

    @staticmethod
    def _infer_platform_hint(payload: dict[str, Any]) -> str:
        """Infer likely runtime platform from native instance metadata."""

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
