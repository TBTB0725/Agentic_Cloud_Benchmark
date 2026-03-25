"""Runtime configuration models for the ACBench prototype."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RunConfig:
    """Top-level run configuration passed into executors."""

    dry_run: bool = False
    max_steps: int = 10
    keep_artifacts: bool = True
    aiops_agent_type: str = "unconfigured"
    code_agent_type: str = "unconfigured"
    aiops_agent_ref: str = ""
    code_agent_ref: str = ""
    code_patch_path: str = ""
    openai_model: str = ""
    openai_api_key_env: str = "OPENAI_API_KEY"
    openai_base_url: str = ""
