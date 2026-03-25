"""Scenario-level readiness checks for the ACBench prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from acbench.adapters.aiopslab import AIOpsLabExecutor
from acbench.adapters.swebench import SWEBenchCodeExecutor
from acbench.backends.ops.native_upstream import (
    has_problem_id as aiopslab_has_problem_id,
    inspect_native_environment as inspect_aiopslab_native_environment,
)
from acbench.doctor import inspect_acbench_code_backend, inspect_aiopslab
from acbench.models.scenario import ScenarioSpec


@dataclass(slots=True)
class ReadinessIssue:
    """One readiness issue detected for a scenario."""

    level: str
    source: str
    message: str


@dataclass(slots=True)
class ScenarioReadinessReport:
    """Readiness report for a scenario under the current environment."""

    scenario_id: str
    ready_for_dry_run: bool
    ready_for_live_run: bool
    issues: list[ReadinessIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "ready_for_dry_run": self.ready_for_dry_run,
            "ready_for_live_run": self.ready_for_live_run,
            "issues": [asdict(issue) for issue in self.issues],
        }


def check_scenario_readiness(scenario: ScenarioSpec) -> ScenarioReadinessReport:
    """Check whether a scenario is runnable under the current environment."""

    issues: list[ReadinessIssue] = []

    if scenario.ops_fault and scenario.ops_fault.source == "aiopslab":
        if not aiopslab_has_problem_id(scenario.ops_fault.problem_id):
            issues.append(
                ReadinessIssue(
                    level="error",
                    source="aiopslab",
                    message=(
                        "Unknown AIOpsLab problem_id "
                        f"`{scenario.ops_fault.problem_id}`."
                    ),
                )
            )
        aiops = inspect_aiopslab_native_environment()
        aiops_env = inspect_aiopslab(Path(aiops.repo_root))
        if not aiops.import_ready:
            issues.append(
                ReadinessIssue(
                    level="error",
                    source="aiopslab",
                    message=(
                        "AIOpsLab backend is not import-ready. Missing dependency: "
                        f"{aiops.missing_dependency or 'unknown'}."
                    ),
                )
            )
        if not aiops_env.extra_checks.get("config_exists", False):
            issues.append(
                ReadinessIssue(
                    level="error",
                    source="aiopslab",
                    message="AIOpsLab config.yml is missing.",
                )
            )
        if not aiops_env.extra_checks.get("kubectl_current_context", ""):
            issues.append(
                ReadinessIssue(
                    level="error",
                    source="aiopslab",
                    message="kubectl current-context is not available.",
                )
            )
        if not aiops_env.extra_checks.get("cluster_reachable", False):
            issues.append(
                ReadinessIssue(
                    level="error",
                    source="aiopslab",
                    message="kubectl cluster-info cannot reach the current cluster.",
                )
            )
        helm_present = any(
            check.name == "helm" and check.available
            for check in aiops_env.recommended_commands
        )
        if not helm_present:
            issues.append(
                ReadinessIssue(
                    level="error",
                    source="aiopslab",
                    message="helm is not available on PATH.",
                )
            )
    elif scenario.ops_fault and scenario.ops_fault.source not in {"aiopslab", "acbench"}:
        issues.append(
            ReadinessIssue(
                level="error",
                source="scenario",
                message=f"Unsupported ops fault source: {scenario.ops_fault.source}",
            )
        )

    if scenario.mode in {"code_only", "combined"}:
        native_swebench_instance = (
            scenario.code_fault is not None
            and scenario.code_fault.source == "swe-bench-live"
            and bool(scenario.code_fault.instance_path)
        )
        repo_backed_swe_style_task = (
            scenario.code_fault is not None
            and scenario.code_fault.source == "swe-bench-live"
            and not native_swebench_instance
        )

        if native_swebench_instance:
            instance_path = Path(scenario.code_fault.instance_path)
            if not instance_path.is_absolute():
                instance_path = Path.cwd() / instance_path
            if not instance_path.exists():
                issues.append(
                    ReadinessIssue(
                        level="error",
                        source="scenario",
                        message=f"SWE-bench-Live instance_path does not exist: {instance_path}",
                    )
                )
            else:
                native_info = SWEBenchCodeExecutor.inspect_native_instance_file(instance_path)
                if native_info["missing_fields"]:
                    issues.append(
                        ReadinessIssue(
                            level="error",
                            source="scenario",
                            message=(
                                "SWE-bench-Live instance is missing required fields: "
                                + ", ".join(native_info["missing_fields"])
                            ),
                        )
                    )
                if not native_info["has_docker_image"]:
                    issues.append(
                        ReadinessIssue(
                            level="warning",
                            source="scenario",
                            message="SWE-bench-Live instance does not declare docker_image; upstream runtime may fall back to a default image name.",
                        )
                    )
        elif scenario.service.repository_path:
            repo_path = Path(scenario.service.repository_path)
            if not repo_path.is_absolute():
                repo_path = Path.cwd() / repo_path
            if not repo_path.exists():
                issues.append(
                    ReadinessIssue(
                        level="error",
                        source="scenario",
                        message=f"Repository path does not exist: {repo_path}",
                    )
                )
        elif not native_swebench_instance:
            issues.append(
                ReadinessIssue(
                    level="warning",
                    source="scenario",
                    message="repository_path is not set for a code-capable scenario.",
                )
            )

        if not native_swebench_instance and not scenario.build.test_cmds:
            issues.append(
                ReadinessIssue(
                    level="warning",
                    source="scenario",
                    message="No test_cmds defined for code scenario.",
                )
            )

        if native_swebench_instance and scenario.code_fault and scenario.code_fault.source == "swe-bench-live":
            swe = SWEBenchCodeExecutor.preflight()
            if not swe.import_ready:
                issues.append(
                    ReadinessIssue(
                        level="error",
                        source="swe-bench-live-native",
                        message=(
                            "SWE-bench-Live native backend is not import-ready. Missing dependency: "
                            f"{swe.missing_dependency or 'unknown'}."
                        ),
                    )
                )
        elif repo_backed_swe_style_task:
            acbench_code = inspect_acbench_code_backend()
            git_present = any(
                check.name == "git" and check.available
                for check in acbench_code.recommended_commands
            )
            if not git_present:
                issues.append(
                    ReadinessIssue(
                        level="warning",
                        source="acbench-code",
                        message="git is not available; standalone code runs can still work, but diff capture may be limited.",
                    )
                )
        elif scenario.code_fault and scenario.code_fault.source not in {"acbench", "swe-bench-live"}:
            issues.append(
                ReadinessIssue(
                    level="error",
                    source="scenario",
                    message=f"Unsupported code fault source: {scenario.code_fault.source}",
                )
            )

    ready_for_dry_run = not any(issue.level == "error" and issue.source == "scenario" for issue in issues)
    ready_for_live_run = not any(issue.level == "error" for issue in issues)
    return ScenarioReadinessReport(
        scenario_id=scenario.scenario_id,
        ready_for_dry_run=ready_for_dry_run,
        ready_for_live_run=ready_for_live_run,
        issues=issues,
    )
