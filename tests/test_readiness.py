"""Tests for scenario readiness checks."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from acbench.models.scenario import ScenarioSpec
from acbench.validate import check_scenario_readiness


class ReadinessTests(unittest.TestCase):
    def test_missing_repository_path_is_reported(self) -> None:
        scenario = ScenarioSpec.from_dict(
            {
                "scenario_id": "code-missing-repo",
                "title": "missing repo",
                "mode": "code_only",
                "service": {
                    "application": "app",
                    "service": "svc",
                    "repository_path": "does-not-exist",
                },
                "code_fault": {
                    "source": "acbench",
                    "defect_id": "d1",
                },
                "build": {
                    "test_cmds": ["echo ok"],
                },
            }
        )

        report = check_scenario_readiness(scenario)
        self.assertFalse(report.ready_for_live_run)
        self.assertTrue(
            any("Repository path does not exist" in issue.message for issue in report.issues)
        )

    def test_native_swebench_instance_path_bypasses_repository_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_path = Path(tmp_dir) / "instance.json"
            instance_path.write_text(
                json.dumps(
                    {
                        "instance_id": "native-1",
                        "repo": "owner/repo",
                        "base_commit": "abc123",
                        "patch": "diff --git a/x b/x",
                        "test_patch": "",
                        "docker_image": "example/native:latest",
                        "PASS_TO_PASS": [],
                        "FAIL_TO_PASS": [],
                    }
                ),
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

            report = check_scenario_readiness(scenario)

            self.assertFalse(
                any("Repository path does not exist" in issue.message for issue in report.issues)
            )

    def test_native_swebench_missing_required_fields_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_path = Path(tmp_dir) / "instance.json"
            instance_path.write_text(
                json.dumps(
                    {
                        "instance_id": "native-1",
                        "repo": "owner/repo",
                    }
                ),
                encoding="utf-8",
            )
            scenario = ScenarioSpec.from_dict(
                {
                    "scenario_id": "native-swebench-incomplete",
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

            report = check_scenario_readiness(scenario)

            self.assertTrue(
                any("missing required fields" in issue.message for issue in report.issues)
            )
            self.assertFalse(report.ready_for_live_run)

    @mock.patch("acbench.validate.SWEBenchCodeExecutor.preflight")
    def test_repo_backed_swe_style_task_does_not_require_upstream_import_ready(
        self,
        mock_preflight,
    ) -> None:
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
        mock_preflight.return_value.import_ready = False
        mock_preflight.return_value.missing_dependency = "docker"

        report = check_scenario_readiness(scenario)

        self.assertFalse(
            any(issue.source == "swe-bench-live" and issue.level == "error" for issue in report.issues)
        )
        self.assertTrue(report.ready_for_live_run)

    @mock.patch("acbench.validate.SWEBenchCodeExecutor.preflight")
    def test_native_swebench_import_failure_uses_native_backend_name(
        self,
        mock_preflight,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_path = Path(tmp_dir) / "instance.json"
            instance_path.write_text(
                json.dumps(
                    {
                        "instance_id": "native-1",
                        "repo": "owner/repo",
                        "patch": "p",
                        "test_patch": "t",
                        "PASS_TO_PASS": [],
                        "FAIL_TO_PASS": [],
                        "test_cmds": ["pytest"],
                        "docker_image": "example/native:latest",
                    }
                ),
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
            mock_preflight.return_value.import_ready = False
            mock_preflight.return_value.missing_dependency = "docker"

            report = check_scenario_readiness(scenario)

            self.assertTrue(
                any(
                    issue.source == "swe-bench-live-native"
                    and issue.level == "error"
                    and "native backend is not import-ready" in issue.message
                    for issue in report.issues
                )
            )


if __name__ == "__main__":
    unittest.main()
