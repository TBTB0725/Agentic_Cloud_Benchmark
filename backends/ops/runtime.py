"""Internal runtime models for future ACBench-owned ops backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from acbench.models.result import ExecutorResult
from acbench.models.result import _json_safe
from acbench.models.scenario import ScenarioSpec


@dataclass(slots=True)
class NativeOpsProblem:
    """Normalized ops-task description used by internal ACBench backends."""

    problem_id: str
    source: str
    application: str
    service: str
    description: str = ""
    deployment: str = "k8s"
    require_detection: bool = False
    require_localization: bool = False
    require_repair: bool = False

    @classmethod
    def from_scenario(cls, scenario: ScenarioSpec) -> "NativeOpsProblem":
        """Build one normalized ops problem from a scenario."""

        if scenario.ops_fault is None:
            raise ValueError(f"Scenario {scenario.scenario_id} does not contain an ops fault.")
        return cls(
            problem_id=scenario.ops_fault.problem_id,
            source=scenario.ops_fault.source,
            application=scenario.service.application,
            service=scenario.service.service,
            description=scenario.ops_fault.description,
            deployment=scenario.service.deployment,
            require_detection=scenario.success_criteria.require_detection,
            require_localization=scenario.success_criteria.require_localization,
            require_repair=scenario.success_criteria.require_repair,
        )


@dataclass(slots=True)
class OpsRunRequest:
    """Execution request for one internal ops backend run."""

    problem: NativeOpsProblem
    output_dir: Path
    max_steps: int = 10
    agent_ref: str = ""
    keep_artifacts: bool = True


@dataclass(slots=True)
class OpsRunOutcome:
    """Normalized result produced by an internal ops backend run."""

    detected: bool = False
    localized: bool = False
    repaired: bool = False
    success: bool = False
    metrics: dict[str, object] = field(default_factory=dict)
    logs: dict[str, str] = field(default_factory=dict)
    details: dict[str, object] = field(default_factory=dict)

    def to_executor_payload(self, backend_name: str) -> dict[str, object]:
        """Convert the outcome into a stable executor-like payload."""

        return {
            "backend": backend_name,
            "success": self.success,
            "detected": self.detected,
            "localized": self.localized,
            "repaired": self.repaired,
            "metrics": _json_safe(dict(self.metrics)),
            "logs": _json_safe(dict(self.logs)),
            "details": _json_safe(dict(self.details)),
        }

    def to_executor_result(self, backend_name: str) -> ExecutorResult:
        """Convert the outcome into a normalized executor result."""

        return ExecutorResult(
            backend=backend_name,
            success=self.success,
            detected=self.detected,
            localized=self.localized,
            repaired=self.repaired,
            metrics=_json_safe(dict(self.metrics)),
            logs=_json_safe(dict(self.logs)),
            details=_json_safe(dict(self.details)),
        )
