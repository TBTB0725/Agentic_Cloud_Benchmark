"""Adapter utilities for integrating AIOpsLab into ACBench."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from acbench.agents.loader import load_object
from acbench.backends.ops.native_upstream import (
    NativeAIOpsEnvironment,
    discover_problem_ids,
    ensure_helm_homes,
    ensure_tooling_on_path,
    has_problem_id,
    inspect_native_environment,
    registry_path,
    resolve_native_repo_root,
)
from acbench.backends.ops.runner import build_ops_request, write_ops_artifacts
from acbench.backends.ops.runtime import NativeOpsProblem, OpsRunOutcome
from acbench.executors.base import BenchmarkExecutor
from acbench.models.result import ExecutorResult
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec

AIOpsLabPreflight = NativeAIOpsEnvironment


class AIOpsLabExecutor(BenchmarkExecutor):
    """Adapter surface for future AIOpsLab integration."""

    def __init__(self) -> None:
        super().__init__(backend_name="aiopslab")

    def execute(
        self,
        scenario: ScenarioSpec,
        run_dir: Path,
        run_config: RunConfig,
    ) -> ExecutorResult:
        preflight = self.preflight()
        if not preflight.import_ready:
            raise RuntimeError(
                "AIOpsLab backend is not import-ready in this environment. "
                f"Missing dependency: {preflight.missing_dependency or 'unknown'}."
            )
        if not run_config.aiops_agent_ref:
            raise RuntimeError(
                "AIOpsLab execution requires `aiops_agent_ref` in RunConfig, "
                "for example `acbench.agents.scripted:SubmitOnlyAIOpsAgent`."
            )

        repo_root = self.resolve_repo_root()
        ensure_tooling_on_path(repo_root)
        ensure_helm_homes(run_dir)
        sys.path.insert(0, str(repo_root))
        try:
            from aiopslab.orchestrator.orchestrator import Orchestrator

            agent_cls = load_object(run_config.aiops_agent_ref)
            agent = agent_cls()
            if hasattr(agent, "configure"):
                agent.configure(run_config)
            orchestrator = Orchestrator(results_dir=run_dir)
            orchestrator.register_agent(agent, name=run_config.aiops_agent_ref)
            problem_desc, instructions, apis = orchestrator.init_problem(
                scenario.ops_fault.problem_id
            )
            if hasattr(agent, "init_context"):
                agent.init_context(problem_desc, instructions, apis)
            live_result = asyncio.run(
                orchestrator.start_problem(max_steps=run_config.max_steps)
            )
            if hasattr(agent, "last_prompt") and getattr(agent, "last_prompt", ""):
                (run_dir / "aiops_agent_prompt.txt").write_text(
                    str(agent.last_prompt),
                    encoding="utf-8",
                )
            if hasattr(agent, "last_response") and getattr(agent, "last_response", ""):
                (run_dir / "aiops_agent_response.txt").write_text(
                    str(agent.last_response),
                    encoding="utf-8",
                )
            if hasattr(agent, "last_action") and getattr(agent, "last_action", ""):
                (run_dir / "aiops_agent_action.txt").write_text(
                    str(agent.last_action),
                    encoding="utf-8",
                )
            session = orchestrator.session.to_dict() if orchestrator.session else {}
            problem = NativeOpsProblem.from_scenario(scenario)
            outcome = self._build_live_outcome(
                scenario=scenario,
                live_result=live_result,
                session=session,
            )
            request = build_ops_request(
                problem,
                output_dir=run_dir / "ops_eval",
                max_steps=run_config.max_steps,
                agent_ref=run_config.aiops_agent_ref,
                keep_artifacts=run_config.keep_artifacts,
            )
            enriched = write_ops_artifacts(request, outcome)
            if (run_dir / "aiops_agent_prompt.txt").exists():
                enriched.logs["agent_prompt_path"] = str(run_dir / "aiops_agent_prompt.txt")
            if (run_dir / "aiops_agent_response.txt").exists():
                enriched.logs["agent_response_path"] = str(run_dir / "aiops_agent_response.txt")
            if (run_dir / "aiops_agent_action.txt").exists():
                enriched.logs["agent_action_path"] = str(run_dir / "aiops_agent_action.txt")
            return enriched.to_executor_result(self.backend_name)
        finally:
            if str(repo_root) in sys.path:
                sys.path.remove(str(repo_root))

    @staticmethod
    def resolve_repo_root() -> Path:
        """Resolve the local AIOpsLab repository root."""

        return resolve_native_repo_root()

    @classmethod
    def registry_path(cls) -> Path:
        """Return the path to the AIOpsLab problem registry source file."""

        return registry_path(cls.resolve_repo_root())

    @classmethod
    def discover_problem_ids(cls) -> list[str]:
        """Read problem IDs from the AIOpsLab registry source without importing dependencies."""

        return discover_problem_ids(cls.resolve_repo_root())

    @classmethod
    def has_problem_id(cls, problem_id: str) -> bool:
        """Check whether a problem ID exists in the local AIOpsLab registry."""

        return has_problem_id(problem_id, cls.resolve_repo_root())

    @classmethod
    def preflight(cls) -> AIOpsLabPreflight:
        """Check local repository availability and import readiness."""

        return inspect_native_environment()

    @staticmethod
    def _build_live_outcome(
        scenario: ScenarioSpec,
        live_result: dict,
        session: dict,
    ) -> OpsRunOutcome:
        """Map AIOpsLab execution output into the normalized internal ops outcome."""

        problem = NativeOpsProblem.from_scenario(scenario)
        metrics = dict(live_result.get("results", {}))
        details = {
            "session_id": session.get("session_id", ""),
            "problem_id": problem.problem_id,
            "final_state": live_result.get("final_state", ""),
            "framework_overhead": live_result.get("framework_overhead", None),
            "trace_length": len(session.get("trace", [])),
        }
        detected = AIOpsLabExecutor._metric_is_correct(
            metrics,
            status_key="Detection Accuracy",
            fallback_key="TTD",
        )
        localized = AIOpsLabExecutor._metric_is_correct(
            metrics,
            status_key="Localization Accuracy",
            fallback_key="TTL",
        )
        repaired = AIOpsLabExecutor._metric_is_correct(
            metrics,
            status_key="Repair Accuracy",
            fallback_key="TTM",
        )
        success = True
        if problem.require_detection and not detected:
            success = False
        if problem.require_localization and not localized:
            success = False
        if problem.require_repair and not repaired:
            success = False
        if not metrics:
            success = False
        return OpsRunOutcome(
            detected=detected,
            localized=localized,
            repaired=repaired,
            success=success,
            metrics=metrics,
            details=details,
        )

    @staticmethod
    def _metric_is_correct(
        metrics: dict,
        *,
        status_key: str,
        fallback_key: str,
    ) -> bool:
        """Interpret AIOpsLab status metrics conservatively."""

        status = metrics.get(status_key)
        if status is not None:
            normalized = str(status).strip().lower()
            return normalized == "correct"
        return fallback_key in metrics
