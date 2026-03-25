"""Environment diagnostics for the ACBench prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib


def _module_available(module_name: str) -> bool:
    """Return whether a Python module can be imported."""

    return importlib.util.find_spec(module_name) is not None


def _command_available(command_name: str) -> bool:
    """Return whether a shell command is available on PATH."""

    return shutil.which(command_name) is not None


def _resolve_command(command_name: str, repo_root: Path | None = None) -> str | None:
    """Resolve a command from PATH or known bundled tool locations."""

    resolved = shutil.which(command_name)
    if resolved:
        return resolved

    if repo_root is None:
        return None

    candidates = [
        repo_root / "tools" / "bin" / command_name,
        repo_root / "tools" / "bin" / f"{command_name}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


@dataclass(slots=True)
class ToolCheck:
    """Single package or command check result."""

    name: str
    available: bool


@dataclass(slots=True)
class ProjectDoctorReport:
    """Environment diagnostics for one backend project."""

    name: str
    repo_root: str
    python_version: str
    declared_dependencies: list[str] = field(default_factory=list)
    required_modules: list[ToolCheck] = field(default_factory=list)
    recommended_commands: list[ToolCheck] = field(default_factory=list)
    extra_checks: dict[str, object] = field(default_factory=dict)
    next_actions: list[str] = field(default_factory=list)

    @property
    def import_ready(self) -> bool:
        return all(check.available for check in self.required_modules)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "repo_root": self.repo_root,
            "python_version": self.python_version,
            "declared_dependencies": list(self.declared_dependencies),
            "required_modules": [asdict(item) for item in self.required_modules],
            "recommended_commands": [asdict(item) for item in self.recommended_commands],
            "extra_checks": dict(self.extra_checks),
            "next_actions": list(self.next_actions),
            "import_ready": self.import_ready,
        }


def _load_dependencies(pyproject_path: Path) -> list[str]:
    """Load string dependencies from a pyproject file when possible."""

    if not pyproject_path.exists():
        return []
    with pyproject_path.open("rb") as handle:
        data = tomllib.load(handle)

    if "project" in data and "dependencies" in data["project"]:
        return list(data["project"]["dependencies"])

    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    return [name for name in poetry_deps.keys() if name != "python"]


def _normalize_import_name(requirement_name: str) -> str:
    """Map package names to import module names conservatively."""

    token = requirement_name.split(">=")[0].split("==")[0].split("^")[0].split("<")[0]
    token = token.split("[")[0].strip()
    return token.replace("-", "_")


def _run_command(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 10,
) -> tuple[bool, str]:
    """Run a command and return a success flag and trimmed output."""

    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except Exception as exc:
        return False, str(exc)

    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def inspect_aiopslab(repo_root: Path) -> ProjectDoctorReport:
    """Collect diagnostics for the local AIOpsLab checkout."""

    pyproject = repo_root / "pyproject.toml"
    dependency_names = _load_dependencies(pyproject)
    core_modules = []
    for name in ("pydantic", "rich", "kubernetes", "prometheus_api_client"):
        core_modules.append(
            ToolCheck(name=name, available=_module_available(name))
        )
    kubectl_cmd = _resolve_command("kubectl")
    helm_cmd = _resolve_command("helm", repo_root=repo_root)
    docker_cmd = _resolve_command("docker")
    commands = [
        ToolCheck(name="kubectl", available=kubectl_cmd is not None),
        ToolCheck(name="helm", available=helm_cmd is not None),
        ToolCheck(name="docker", available=docker_cmd is not None),
    ]
    config_path = repo_root / "aiopslab" / "config.yml"
    current_context = ""
    cluster_reachable = False
    cluster_message = ""
    if kubectl_cmd:
        context_ok, context_out = _run_command([kubectl_cmd, "config", "current-context"])
        if context_ok:
            current_context = context_out
        cluster_ok, cluster_out = _run_command([kubectl_cmd, "cluster-info"], timeout=12)
        cluster_reachable = cluster_ok
        cluster_message = cluster_out
    helm_version = ""
    if helm_cmd:
        helm_ok, helm_out = _run_command([helm_cmd, "version", "--short"])
        if helm_ok:
            helm_version = helm_out
    report = ProjectDoctorReport(
        name="aiopslab",
        repo_root=str(repo_root),
        python_version=sys.version.split()[0],
        declared_dependencies=dependency_names,
        required_modules=core_modules,
        recommended_commands=commands,
        extra_checks={
            "config_path": str(config_path),
            "config_exists": config_path.exists(),
            "kubectl_current_context": current_context,
            "cluster_reachable": cluster_reachable,
            "cluster_message": cluster_message,
            "helm_path": helm_cmd or "",
            "helm_version": helm_version,
        },
    )
    report.next_actions = build_next_actions(report)
    return report


def inspect_swebench_live(repo_root: Path) -> ProjectDoctorReport:
    """Collect diagnostics for the local SWE-bench-Live checkout."""

    pyproject = repo_root / "pyproject.toml"
    launch_pyproject = repo_root / "launch" / "pyproject.toml"
    main_deps = _load_dependencies(pyproject)
    launch_deps = _load_dependencies(launch_pyproject)
    core_modules = []
    for name in ("docker", "datasets", "rich", "git", "langgraph"):
        import_name = "git" if name == "git" else name
        core_modules.append(
            ToolCheck(name=name, available=_module_available(import_name))
        )
    docker_cmd = _resolve_command("docker")
    git_cmd = _resolve_command("git")
    commands = [
        ToolCheck(name="docker", available=docker_cmd is not None),
        ToolCheck(name="git", available=git_cmd is not None),
    ]
    docker_daemon_reachable = False
    docker_daemon_message = ""
    docker_cli_reachable = False
    docker_cli_message = ""
    if docker_cmd:
        docker_ok, docker_out = _run_command(
            [docker_cmd, "info", "--format", "{{json .ServerVersion}}"],
            timeout=12,
        )
        docker_daemon_reachable = docker_ok
        docker_daemon_message = docker_out
        cli_ok, cli_out = _run_command([docker_cmd, "info"], timeout=12)
        docker_cli_reachable = cli_ok
        docker_cli_message = cli_out
    report = ProjectDoctorReport(
        name="swe-bench-live",
        repo_root=str(repo_root),
        python_version=sys.version.split()[0],
        declared_dependencies=main_deps + [f"launch::{dep}" for dep in launch_deps],
        required_modules=core_modules,
        recommended_commands=commands,
        extra_checks={
            "backend_type": "upstream-native",
            "docker_daemon_reachable": docker_daemon_reachable,
            "docker_daemon_message": docker_daemon_message,
            "docker_cli_reachable": docker_cli_reachable,
            "docker_cli_message": docker_cli_message,
        },
    )
    report.next_actions = build_next_actions(report)
    return report


def inspect_acbench_code_backend() -> ProjectDoctorReport:
    """Collect diagnostics for the internal ACBench standalone code backend."""

    git_cmd = _resolve_command("git")
    commands = [
        ToolCheck(name="git", available=git_cmd is not None),
    ]
    report = ProjectDoctorReport(
        name="acbench-code",
        repo_root=str(Path(__file__).resolve().parent),
        python_version=sys.version.split()[0],
        declared_dependencies=[],
        required_modules=[],
        recommended_commands=commands,
        extra_checks={
            "backend_type": "standalone-local-code",
            "git_available": git_cmd is not None,
        },
    )
    report.next_actions = build_next_actions(report)
    return report


def build_next_actions(report: ProjectDoctorReport) -> list[str]:
    """Generate actionable next steps from a project doctor report."""

    actions: list[str] = []
    missing_modules = [item.name for item in report.required_modules if not item.available]
    missing_commands = [item.name for item in report.recommended_commands if not item.available]

    if report.name == "aiopslab":
        if missing_modules:
            actions.append(
                "Install missing AIOpsLab Python modules: " + ", ".join(missing_modules)
            )
        if "helm" in missing_commands:
            actions.append("Install Helm and ensure `helm` is available on PATH.")
        if not report.extra_checks.get("config_exists", False):
            actions.append(
                "Create the upstream AIOps configuration file from its example template "
                "and fill in the cluster values before running live ops scenarios."
            )
        if not report.extra_checks.get("kubectl_current_context", ""):
            actions.append("Set a valid `kubectl` current-context before running live AIOps scenarios.")
        if not report.extra_checks.get("cluster_reachable", False):
            actions.append("Start or fix the current Kubernetes cluster so `kubectl cluster-info` succeeds.")
    elif report.name == "swe-bench-live":
        if missing_modules:
            actions.append(
                "Install missing SWE-bench-Live Python modules: " + ", ".join(missing_modules)
            )
        if "docker" in missing_commands:
            actions.append("Install Docker CLI and ensure `docker` is available on PATH.")
        if not report.extra_checks.get("docker_daemon_reachable", False) and not report.extra_checks.get("docker_cli_reachable", False):
            actions.append("Start Docker Desktop or another Docker daemon so `docker info` succeeds.")
    elif report.name == "acbench-code":
        if "git" in missing_commands:
            actions.append("Install Git to enable patch diff capture for the standalone ACBench code backend.")
    return actions


def build_readiness_bundle(aiopslab_root: Path, swebench_root: Path) -> dict:
    """Build a combined environment readiness report for both backends."""

    aiops = inspect_aiopslab(aiopslab_root)
    swe = inspect_swebench_live(swebench_root)
    acbench_code = inspect_acbench_code_backend()
    return {
        "aiopslab": aiops.to_dict(),
        "acbench_code": acbench_code.to_dict(),
        "swe_bench_live_native": swe.to_dict(),
        "summary": {
            "aiopslab_live_ready": aiops.import_ready
            and bool(aiops.extra_checks.get("config_exists"))
            and bool(aiops.extra_checks.get("kubectl_current_context"))
            and bool(aiops.extra_checks.get("cluster_reachable"))
            and any(item.name == "helm" and item.available for item in aiops.recommended_commands),
            "acbench_code_ready": True,
            "swe_bench_live_native_ready": swe.import_ready
            and (
                bool(swe.extra_checks.get("docker_daemon_reachable"))
                or bool(swe.extra_checks.get("docker_cli_reachable"))
            ),
        },
    }
