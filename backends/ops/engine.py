"""Execution adapters for the internal ACBench ops runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from acbench.backends.ops.native_upstream import resolve_native_repo_root
from acbench.backends.ops.runtime import NativeOpsProblem, OpsRunOutcome, OpsRunRequest


class OpsRuntimeEngine(Protocol):
    """Protocol for pluggable ACBench ops runtime engines."""

    def run(self, request: OpsRunRequest) -> OpsRunOutcome:
        """Execute one ops-task request and return a normalized outcome."""


@dataclass(slots=True)
class StandaloneLocalOpsEngine:
    """ACBench-owned synthetic ops engine for local development and demos."""

    def run(self, request: OpsRunRequest) -> OpsRunOutcome:
        """Produce a deterministic synthetic ops outcome."""

        problem = request.problem
        metrics = {
            "TTD": 1.0 if problem.require_detection else 0.0,
            "TTL": 2.0 if problem.require_localization else 0.0,
            "TTM": 3.0 if problem.require_repair else 0.0,
            "synthetic": True,
        }
        return OpsRunOutcome(
            detected=problem.require_detection,
            localized=problem.require_localization,
            repaired=problem.require_repair,
            success=True,
            metrics=metrics,
            details={
                "mode": "synthetic-local-ops",
                "problem_id": problem.problem_id,
                "max_steps": request.max_steps,
                "agent_ref": request.agent_ref,
            },
        )


@dataclass(slots=True)
class UpstreamAIOpsLabEngine:
    """Temporary bridge marker for the current native AIOpsLab live path."""

    repo_root: Path

    def run(self, request: OpsRunRequest) -> OpsRunOutcome:
        """Placeholder for future engine-level AIOpsLab bridge execution."""

        raise NotImplementedError(
            "UpstreamAIOpsLabEngine is a structural placeholder. "
            "Live AIOpsLab execution still runs through AIOpsLabExecutor."
        )


def build_default_engine() -> OpsRuntimeEngine:
    """Build the current default ops runtime engine."""

    return UpstreamAIOpsLabEngine(repo_root=resolve_native_repo_root())


def build_engine_for_problem(problem: NativeOpsProblem) -> OpsRuntimeEngine:
    """Build the most appropriate current engine for one ops problem."""

    if problem.source == "acbench":
        return StandaloneLocalOpsEngine()
    return build_default_engine()
