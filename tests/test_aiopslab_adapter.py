"""Tests for AIOpsLab adapter helpers."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from acbench.adapters.aiopslab import AIOpsLabExecutor
from acbench.backends.ops.native_upstream import (
    ensure_helm_homes,
    ensure_tooling_on_path,
    inspect_native_environment,
)
from acbench.models.scenario import ScenarioSpec


class AIOpsLabAdapterTests(unittest.TestCase):
    def test_native_upstream_environment_discovers_registry(self) -> None:
        preflight = inspect_native_environment()
        self.assertTrue(preflight.repo_root.endswith("AIOpsLab"))
        self.assertTrue(preflight.registry_path.endswith("registry.py"))
        self.assertGreater(preflight.problem_count, 0)

    def test_registry_discovery_finds_known_problem(self) -> None:
        problem_ids = AIOpsLabExecutor.discover_problem_ids()
        self.assertIn(
            "astronomy_shop_product_catalog_service_failure-detection-1",
            problem_ids,
        )

    def test_ensure_tooling_on_path_prepends_tools_bin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            tools_dir = repo_root / "tools" / "bin"
            tools_dir.mkdir(parents=True, exist_ok=True)
            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = "base-path"
                ensure_tooling_on_path(repo_root)
                self.assertTrue(os.environ["PATH"].startswith(str(tools_dir)))
            finally:
                os.environ["PATH"] = original_path

    def test_ensure_helm_homes_sets_writable_env_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            original = {
                key: os.environ.get(key)
                for key in ("HELM_CONFIG_HOME", "HELM_CACHE_HOME", "HELM_DATA_HOME")
            }
            try:
                ensure_helm_homes(Path(tmp_dir))
                for key in ("HELM_CONFIG_HOME", "HELM_CACHE_HOME", "HELM_DATA_HOME"):
                    self.assertTrue(os.environ[key].startswith(tmp_dir))
                    self.assertTrue(Path(os.environ[key]).exists())
            finally:
                for key, value in original.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_build_live_outcome_maps_metrics_and_success(self) -> None:
        scenario = ScenarioSpec.from_dict(
            {
                "scenario_id": "ops-live-shape",
                "title": "ops",
                "mode": "ops_only",
                "service": {
                    "application": "app",
                    "service": "svc",
                },
                "ops_fault": {
                    "source": "aiopslab",
                    "problem_id": "p-1",
                },
                "success_criteria": {
                    "require_detection": True,
                    "require_localization": True,
                    "require_repair": False,
                },
            }
        )

        outcome = AIOpsLabExecutor._build_live_outcome(
            scenario=scenario,
            live_result={
                "results": {"TTD": 1.0, "TTL": 2.0},
                "final_state": "done",
                "framework_overhead": 0.1,
            },
            session={"session_id": "s-1", "trace": [{"step": 1}]},
        )

        self.assertTrue(outcome.success)
        self.assertTrue(outcome.detected)
        self.assertTrue(outcome.localized)
        self.assertFalse(outcome.repaired)
        self.assertEqual(outcome.details["session_id"], "s-1")
        self.assertEqual(outcome.metrics["TTD"], 1.0)

    def test_build_live_outcome_marks_incorrect_detection_as_failed(self) -> None:
        scenario = ScenarioSpec.from_dict(
            {
                "scenario_id": "ops-detection-incorrect",
                "title": "ops",
                "mode": "ops_only",
                "service": {
                    "application": "app",
                    "service": "svc",
                },
                "ops_fault": {
                    "source": "aiopslab",
                    "problem_id": "p-1",
                },
                "success_criteria": {
                    "require_detection": True,
                },
            }
        )

        outcome = AIOpsLabExecutor._build_live_outcome(
            scenario=scenario,
            live_result={
                "results": {"Detection Accuracy": "Incorrect", "TTD": 1.0},
                "final_state": "done",
            },
            session={"session_id": "s-1", "trace": [{"step": 1}]},
        )

        self.assertFalse(outcome.success)
        self.assertFalse(outcome.detected)


if __name__ == "__main__":
    unittest.main()
