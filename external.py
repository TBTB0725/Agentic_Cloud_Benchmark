"""Helpers for locating external reference repositories during migration."""

from __future__ import annotations

from pathlib import Path


def workspace_root() -> Path:
    """Return the workspace root that currently contains `acbench/`."""

    return Path(__file__).resolve().parents[1]


def acbench_root() -> Path:
    """Return the `acbench/` package root."""

    return Path(__file__).resolve().parent


def aiopslab_root() -> Path:
    """Return the current default AIOpsLab reference repository root."""

    return workspace_root() / "AIOpsLab"


def swebench_live_root() -> Path:
    """Return the current default SWE-bench-Live reference repository root."""

    return workspace_root() / "SWE-bench-Live"
