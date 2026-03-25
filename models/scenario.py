"""Scenario models for the ACBench prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Literal


ScenarioMode = Literal["ops_only", "code_only", "combined"]


@dataclass(slots=True)
class ServiceSpec:
    """Target application and service selection."""

    application: str
    service: str
    deployment: str = "k8s"
    repository_path: str | None = None


@dataclass(slots=True)
class OpsFaultSpec:
    """Operational incident configuration."""

    source: str
    problem_id: str
    description: str = ""


@dataclass(slots=True)
class CodeFaultSpec:
    """Code-level defect configuration."""

    source: str
    defect_id: str
    description: str = ""
    target_files: list[str] = field(default_factory=list)
    instance_path: str = ""
    platform: str = "windows"


@dataclass(slots=True)
class BuildSpec:
    """Repository build and test commands."""

    rebuild_cmds: list[str] = field(default_factory=list)
    test_cmds: list[str] = field(default_factory=list)
    print_cmds: list[str] = field(default_factory=list)
    log_parser: str = ""


@dataclass(slots=True)
class SuccessCriteria:
    """Run success requirements."""

    require_detection: bool = False
    require_localization: bool = False
    require_repair: bool = False
    require_build_success: bool = False
    require_test_success: bool = False
    require_deploy_success: bool = False


@dataclass(slots=True)
class ScenarioSpec:
    """Unified scenario format for ACBench."""

    scenario_id: str
    title: str
    mode: ScenarioMode
    service: ServiceSpec
    ops_fault: OpsFaultSpec | None = None
    code_fault: CodeFaultSpec | None = None
    build: BuildSpec = field(default_factory=BuildSpec)
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    metrics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    gold_patch_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioSpec":
        service = ServiceSpec(**data["service"])
        ops_fault = OpsFaultSpec(**data["ops_fault"]) if data.get("ops_fault") else None
        code_fault = (
            CodeFaultSpec(**data["code_fault"]) if data.get("code_fault") else None
        )
        build = BuildSpec(**data.get("build", {}))
        success_criteria = SuccessCriteria(**data.get("success_criteria", {}))
        scenario = cls(
            scenario_id=data["scenario_id"],
            title=data["title"],
            mode=data["mode"],
            service=service,
            ops_fault=ops_fault,
            code_fault=code_fault,
            build=build,
            success_criteria=success_criteria,
            metrics=list(data.get("metrics", [])),
            tags=list(data.get("tags", [])),
            notes=data.get("notes", ""),
            gold_patch_path=data.get("gold_patch_path", ""),
        )
        scenario.validate()
        return scenario

    @classmethod
    def from_file(cls, path: str | Path) -> "ScenarioSpec":
        scenario_path = Path(path)
        with scenario_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return cls.from_dict(data)

    def validate(self) -> None:
        if self.mode not in {"ops_only", "code_only", "combined"}:
            raise ValueError(f"Unsupported scenario mode: {self.mode}")

        if self.mode in {"ops_only", "combined"} and self.ops_fault is None:
            raise ValueError("ops_fault is required for ops_only and combined scenarios")

        if self.mode in {"code_only", "combined"} and self.code_fault is None:
            raise ValueError("code_fault is required for code_only and combined scenarios")

        if self.mode in {"code_only", "combined"}:
            native_swebench_instance = (
                self.code_fault is not None
                and self.code_fault.source == "swe-bench-live"
                and bool(self.code_fault.instance_path)
            )
            if not native_swebench_instance and not self.build.rebuild_cmds and not self.build.test_cmds:
                raise ValueError(
                    "code_only and combined scenarios require rebuild_cmds or test_cmds"
                )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
