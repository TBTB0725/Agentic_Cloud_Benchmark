"""Native SWE-bench-Live runtime helpers isolated from adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from acbench.doctor import inspect_swebench_live
from acbench.external import swebench_live_root


@dataclass(slots=True)
class NativeSWEBenchEnvironment:
    """Environment snapshot for native upstream SWE-bench-Live execution."""

    repo_root: str
    launch_root: str
    evaluation_root: str
    import_ready: bool
    backend_type: str = "upstream-native"
    missing_dependency: str = ""


def resolve_native_repo_root() -> Path:
    """Resolve the current default native SWE-bench-Live reference checkout."""

    return swebench_live_root()


def inspect_native_environment() -> NativeSWEBenchEnvironment:
    """Inspect import readiness for native upstream SWE-bench-Live execution."""

    repo_root = resolve_native_repo_root()
    launch_root = repo_root / "launch"
    evaluation_root = repo_root / "evaluation"
    doctor = inspect_swebench_live(repo_root)
    import_ready = doctor.import_ready
    missing_dependency = next(
        (item.name for item in doctor.required_modules if not item.available),
        "",
    )

    try:
        sys.path.insert(0, str(repo_root))
        sys.path.insert(0, str(launch_root))
        from evaluation.evaluation import run_instances  # noqa: F401
        from launch.core.runtime import SetupRuntime  # noqa: F401

        import_ready = True
    except ModuleNotFoundError as exc:
        missing_dependency = exc.name or missing_dependency or str(exc)
    finally:
        for path in (str(launch_root), str(repo_root)):
            if path in sys.path:
                sys.path.remove(path)

    return NativeSWEBenchEnvironment(
        repo_root=str(repo_root),
        launch_root=str(launch_root),
        evaluation_root=str(evaluation_root),
        import_ready=import_ready,
        backend_type="upstream-native",
        missing_dependency=missing_dependency,
    )
