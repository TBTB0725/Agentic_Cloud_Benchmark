"""Standalone ops-task runner for the internal ACBench ops backend."""

from __future__ import annotations

import json
from pathlib import Path

from acbench.backends.ops.engine import build_engine_for_problem
from acbench.backends.ops.runtime import NativeOpsProblem, OpsRunOutcome, OpsRunRequest
from acbench.models.result import _json_safe


def run_ops_request(request: OpsRunRequest) -> OpsRunOutcome:
    """Run one ops request through the currently selected internal ops engine."""

    return build_engine_for_problem(request.problem).run(request)


def write_ops_artifacts(
    request: OpsRunRequest,
    outcome: OpsRunOutcome,
) -> OpsRunOutcome:
    """Write stable ops artifacts for one run and return an enriched outcome."""

    output_dir = Path(request.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outcome_path = output_dir / "ops_outcome.json"
    trace_path = output_dir / "ops_trace.json"

    outcome_payload = {
        "problem_id": request.problem.problem_id,
        "source": request.problem.source,
        "application": request.problem.application,
        "service": request.problem.service,
        "success": outcome.success,
        "detected": outcome.detected,
        "localized": outcome.localized,
        "repaired": outcome.repaired,
        "metrics": _json_safe(dict(outcome.metrics)),
        "details": _json_safe(dict(outcome.details)),
    }
    trace_payload = {
        "problem_id": request.problem.problem_id,
        "agent_ref": request.agent_ref,
        "max_steps": request.max_steps,
        "events": [
            {
                "type": "ops_run_started",
                "source": request.problem.source,
                "service": request.problem.service,
            },
            {
                "type": "ops_run_completed",
                "success": outcome.success,
                "detected": outcome.detected,
                "localized": outcome.localized,
                "repaired": outcome.repaired,
            },
        ],
    }

    outcome_path.write_text(json.dumps(_json_safe(outcome_payload), indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps(_json_safe(trace_payload), indent=2), encoding="utf-8")

    outcome.logs["outcome_path"] = str(outcome_path)
    outcome.logs["trace_path"] = str(trace_path)
    return outcome


def build_ops_request(
    problem: NativeOpsProblem,
    *,
    output_dir,
    max_steps: int = 10,
    agent_ref: str = "",
    keep_artifacts: bool = True,
) -> OpsRunRequest:
    """Build one normalized ops run request."""

    return OpsRunRequest(
        problem=problem,
        output_dir=output_dir,
        max_steps=max_steps,
        agent_ref=agent_ref,
        keep_artifacts=keep_artifacts,
    )
