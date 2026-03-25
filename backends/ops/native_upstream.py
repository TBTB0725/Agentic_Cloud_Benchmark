"""Native AIOpsLab runtime helpers isolated from adapters."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Iterable

from acbench.doctor import inspect_aiopslab
from acbench.external import aiopslab_root


@dataclass(slots=True)
class NativeAIOpsEnvironment:
    """Environment snapshot for native upstream AIOpsLab execution."""

    repo_root: str
    registry_path: str
    problem_count: int
    import_ready: bool
    missing_dependency: str = ""


def resolve_native_repo_root() -> Path:
    """Resolve the current default AIOpsLab reference checkout."""

    return aiopslab_root()


def registry_path(repo_root: Path | None = None) -> Path:
    """Return the path to the AIOpsLab problem registry source file."""

    resolved_root = repo_root or resolve_native_repo_root()
    return resolved_root / "aiopslab" / "orchestrator" / "problems" / "registry.py"


def discover_problem_ids(repo_root: Path | None = None) -> list[str]:
    """Read problem IDs from the AIOpsLab registry without importing upstream code."""

    registry_file = registry_path(repo_root)
    tree = ast.parse(registry_file.read_text(encoding="utf-8"))
    found: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr != "PROBLEM_REGISTRY":
                continue
            if not isinstance(node.value, ast.Dict):
                continue
            found.extend(_extract_string_keys(node.value.keys))
    return found


def has_problem_id(problem_id: str, repo_root: Path | None = None) -> bool:
    """Check whether a problem ID exists in the local AIOpsLab registry."""

    return problem_id in set(discover_problem_ids(repo_root))


def inspect_native_environment() -> NativeAIOpsEnvironment:
    """Inspect import readiness and registry availability for native AIOpsLab execution."""

    repo_root = resolve_native_repo_root()
    ensure_tooling_on_path(repo_root)
    ensure_helm_homes(repo_root / ".acbench_helm")
    registry_file = registry_path(repo_root)
    problem_ids = discover_problem_ids(repo_root) if registry_file.exists() else []
    doctor = inspect_aiopslab(repo_root)
    import_ready = doctor.import_ready
    missing_dependency = next(
        (item.name for item in doctor.required_modules if not item.available),
        "",
    )

    try:
        sys.path.insert(0, str(repo_root))
        from aiopslab.orchestrator.orchestrator import Orchestrator  # noqa: F401

        import_ready = True
    except ModuleNotFoundError as exc:
        import_ready = False
        missing_dependency = exc.name or missing_dependency or str(exc)
    finally:
        if str(repo_root) in sys.path:
            sys.path.remove(str(repo_root))

    return NativeAIOpsEnvironment(
        repo_root=str(repo_root),
        registry_path=str(registry_file),
        problem_count=len(problem_ids),
        import_ready=import_ready,
        missing_dependency=missing_dependency,
    )


def ensure_tooling_on_path(repo_root: Path) -> None:
    """Make bundled AIOpsLab tool binaries visible to child processes."""

    tools_dir = repo_root / "tools" / "bin"
    if not tools_dir.exists():
        return
    current_path = os.environ.get("PATH", "")
    tools_str = str(tools_dir)
    entries = current_path.split(os.pathsep) if current_path else []
    if tools_str not in entries:
        os.environ["PATH"] = os.pathsep.join([tools_str, current_path]) if current_path else tools_str


def ensure_helm_homes(base_dir: Path) -> None:
    """Set writable Helm home directories for the current process."""

    helm_root = base_dir / "helm_home"
    config_home = helm_root / "config"
    cache_home = helm_root / "cache"
    data_home = helm_root / "data"
    for path in (config_home, cache_home, data_home):
        path.mkdir(parents=True, exist_ok=True)
    os.environ["HELM_CONFIG_HOME"] = str(config_home)
    os.environ["HELM_CACHE_HOME"] = str(cache_home)
    os.environ["HELM_DATA_HOME"] = str(data_home)


def _extract_string_keys(keys: Iterable[ast.expr | None]) -> list[str]:
    """Extract literal string keys from a dictionary AST node."""

    found: list[str] = []
    for key in keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            found.append(key.value)
    return found
