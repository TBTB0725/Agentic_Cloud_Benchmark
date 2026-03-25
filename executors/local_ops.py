"""Local synthetic ops executor for early combined-scenario validation."""

from __future__ import annotations

from pathlib import Path

from acbench.backends.ops.runner import build_ops_request, run_ops_request, write_ops_artifacts
from acbench.backends.ops.runtime import NativeOpsProblem
from acbench.executors.base import BenchmarkExecutor
from acbench.models.result import ExecutorResult
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


class LocalOpsExecutor(BenchmarkExecutor):
    """Produce a minimal synthetic ops result without external dependencies."""

    def __init__(self) -> None:
        super().__init__(backend_name="acbench-local-ops")

    def execute(
        self,
        scenario: ScenarioSpec,
        run_dir: Path,
        run_config: RunConfig,
    ) -> ExecutorResult:
        problem = NativeOpsProblem.from_scenario(scenario)
        request = build_ops_request(
            problem,
            output_dir=run_dir / "ops_eval",
            max_steps=run_config.max_steps,
            agent_ref=run_config.aiops_agent_ref,
            keep_artifacts=run_config.keep_artifacts,
        )
        outcome = write_ops_artifacts(request, run_ops_request(request))
        return outcome.to_executor_result(self.backend_name)
