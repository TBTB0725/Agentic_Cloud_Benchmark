"""Execution adapters for the internal ACBench code runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Protocol

from acbench.backends.code.runner import run_local_code_request
from acbench.backends.code.runtime import CodeRunOutcome, CodeRunRequest, NativeCodeInstance
from acbench.external import swebench_live_root


class CodeRuntimeEngine(Protocol):
    """Protocol for pluggable ACBench code runtime engines."""

    def run(self, request: CodeRunRequest) -> CodeRunOutcome:
        """Execute one code-task request and return a normalized outcome."""


@dataclass(slots=True)
class StandaloneLocalEngine:
    """ACBench-owned local code engine for repository-backed code tasks."""

    def run(self, request: CodeRunRequest) -> CodeRunOutcome:
        """Run one request through the internal standalone local code runner."""

        return run_local_code_request(request)


@dataclass(slots=True)
class UpstreamSWEBenchEngine:
    """Temporary bridge engine that delegates to upstream SWE-bench-Live runtime."""

    repo_root: Path

    def run(self, request: CodeRunRequest) -> CodeRunOutcome:
        """Run one request through upstream `evaluation.run_instance()`."""

        report = self._run_upstream_instance(
            instance=request.instance,
            output_dir=request.output_dir,
        )
        pass_to_pass = report.get("PASS_TO_PASS", {})
        fail_to_pass = report.get("FAIL_TO_PASS", {})
        return CodeRunOutcome(
            resolved=bool(report.get("resolved", False)),
            pass_to_pass_success=list(
                pass_to_pass.get("success", request.instance.pass_to_pass)
            ),
            pass_to_pass_failure=list(pass_to_pass.get("failure", [])),
            fail_to_pass_success=list(
                fail_to_pass.get("success", request.instance.fail_to_pass)
            ),
            fail_to_pass_failure=list(fail_to_pass.get("failure", [])),
            logs=dict(report.get("logs", {})),
            details={
                "raw_report": report,
            },
        )

    def _run_upstream_instance(
        self,
        instance: NativeCodeInstance,
        output_dir: Path,
    ) -> dict:
        """Call the upstream SWE-bench-Live single-instance helper."""

        repo_root = self.repo_root
        sys.path.insert(0, str(repo_root))
        sys.path.insert(0, str(repo_root / "launch"))
        try:
            from evaluation.evaluation import run_instance

            output_dir.mkdir(parents=True, exist_ok=True)
            return run_instance(
                instance=instance.to_payload(),
                platform=instance.platform,
                output_dir=str(output_dir),
                overwrite=True,
            )
        finally:
            for path in (str(repo_root / "launch"), str(repo_root)):
                if path in sys.path:
                    sys.path.remove(path)


def build_default_engine() -> CodeRuntimeEngine:
    """Build the current default code runtime engine."""

    return UpstreamSWEBenchEngine(repo_root=swebench_live_root())


def build_engine_for_instance(instance: NativeCodeInstance) -> CodeRuntimeEngine:
    """Build the most appropriate current engine for one runtime instance."""

    repo_path = Path(instance.repo) if instance.repo else None
    if repo_path is not None and repo_path.exists() and not instance.docker_image:
        return StandaloneLocalEngine()
    return build_default_engine()
