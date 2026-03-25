"""Tests for SWE-bench-Live adapter helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from acbench.adapters.swebench import SWEBenchCodeExecutor
from acbench.backends.code.native_upstream import inspect_native_environment
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


class SWEBenchAdapterTests(unittest.TestCase):
    def test_native_upstream_environment_detects_repo_layout(self) -> None:
        preflight = inspect_native_environment()
        self.assertTrue(preflight.repo_root.endswith("SWE-bench-Live"))
        self.assertTrue(preflight.launch_root.endswith("SWE-bench-Live\\launch"))
        self.assertEqual(preflight.backend_type, "upstream-native")

    def test_preflight_detects_repo_layout(self) -> None:
        preflight = SWEBenchCodeExecutor.preflight()
        self.assertTrue(preflight.repo_root.endswith("SWE-bench-Live"))
        self.assertTrue(preflight.launch_root.endswith("SWE-bench-Live\\launch"))
        self.assertEqual(preflight.backend_type, "upstream-native")

    def test_standalone_preflight_uses_internal_backend_type(self) -> None:
        preflight = SWEBenchCodeExecutor.standalone_preflight()
        self.assertEqual(preflight.backend_type, "standalone-local-code")
        self.assertTrue(preflight.import_ready)

    def test_preflight_for_repo_backed_scenario_uses_standalone_path(self) -> None:
        scenario = ScenarioSpec.from_dict(
            {
                "scenario_id": "repo-backed-swe-style",
                "title": "repo backed",
                "mode": "code_only",
                "service": {
                    "application": "app",
                    "service": "svc",
                    "repository_path": str(Path.cwd()),
                },
                "code_fault": {
                    "source": "swe-bench-live",
                    "defect_id": "d1",
                },
                "build": {
                    "test_cmds": ["echo ok"],
                },
            }
        )

        preflight = SWEBenchCodeExecutor.preflight_for_scenario(scenario)

        self.assertEqual(preflight.backend_type, "standalone-local-code")

    def test_preflight_for_native_instance_uses_upstream_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_path = Path(tmp_dir) / "instance.json"
            instance_path.write_text(
                '{"instance_id":"native-1","repo":"owner/repo","patch":"p","test_patch":"t","PASS_TO_PASS":[],"FAIL_TO_PASS":[],"test_cmds":["pytest"],"docker_image":"example/native:latest"}',
                encoding="utf-8",
            )
            scenario = ScenarioSpec.from_dict(
                {
                    "scenario_id": "native-swebench",
                    "title": "native",
                    "mode": "code_only",
                    "service": {
                        "application": "app",
                        "service": "svc",
                    },
                    "code_fault": {
                        "source": "swe-bench-live",
                        "defect_id": "d1",
                        "instance_path": str(instance_path),
                        "platform": "linux",
                    },
                }
            )

            preflight = SWEBenchCodeExecutor.preflight_for_scenario(scenario)

            self.assertEqual(preflight.backend_type, "upstream-native")

    def test_execute_rejects_non_native_scenario(self) -> None:
        scenario = ScenarioSpec.from_dict(
            {
                "scenario_id": "repo-backed-swe-style",
                "title": "repo backed",
                "mode": "code_only",
                "service": {
                    "application": "app",
                    "service": "svc",
                    "repository_path": str(Path.cwd()),
                },
                "code_fault": {
                    "source": "swe-bench-live",
                    "defect_id": "d1",
                },
                "build": {
                    "test_cmds": ["echo ok"],
                },
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                SWEBenchCodeExecutor().execute(
                    scenario,
                    Path(tmp_dir),
                    RunConfig(dry_run=False),
                )


if __name__ == "__main__":
    unittest.main()
