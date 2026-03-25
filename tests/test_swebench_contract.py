"""Tests for SWE-bench-Live adapter contract helpers."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from acbench.adapters.swebench import SWEBenchCodeExecutor
from acbench.backends.code.runtime import CodeRunOutcome
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


class SWEBenchContractTests(unittest.TestCase):
    def test_build_instance_payload_rejects_repo_backed_scenario(self) -> None:
        scenario = ScenarioSpec.from_dict(
            {
                "scenario_id": "swe-bridge",
                "title": "bridge",
                "mode": "code_only",
                "service": {
                    "application": "app",
                    "service": "svc",
                    "repository_path": "repo",
                },
                "code_fault": {
                    "source": "swe-bench-live",
                    "defect_id": "d1",
                },
                "build": {
                    "rebuild_cmds": ["build"],
                    "test_cmds": ["test"],
                },
            }
        )

        with self.assertRaises(ValueError):
            SWEBenchCodeExecutor.build_instance_payload(
                scenario,
                RunConfig(dry_run=False),
            )

    def test_build_instance_payload_from_native_instance_path(self) -> None:
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
                        "PASS_TO_PASS": ["t1"],
                        "FAIL_TO_PASS": ["t2"],
                        "test_cmds": ["pytest"],
                        "rebuild_cmds": ["build"],
                    }
                ),
                encoding="utf-8",
            )
            scenario = ScenarioSpec.from_dict(
                {
                    "scenario_id": "native-bridge",
                    "title": "bridge",
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

            payload = SWEBenchCodeExecutor.build_instance_payload(
                scenario,
                RunConfig(dry_run=False),
            )

            self.assertEqual(payload["instance_id"], "native-1")
            self.assertEqual(payload["docker_image"], "example/native:latest")
            self.assertEqual(payload["pred_patch"], "diff --git a/x b/x")
            self.assertEqual(payload["platform"], "linux")

    def test_normalize_report_maps_resolution_fields(self) -> None:
        instance = {
            "instance_id": "swe-bridge",
            "PASS_TO_PASS": ["t1"],
            "FAIL_TO_PASS": ["t2"],
        }
        report = {
            "instance_id": "swe-bridge",
            "resolved": True,
            "PASS_TO_PASS": {"success": ["t1"], "failure": []},
            "FAIL_TO_PASS": {"success": ["t2"], "failure": []},
        }

        result = SWEBenchCodeExecutor.normalize_report(report, instance)

        self.assertTrue(result.success)
        self.assertEqual(result.pass_to_pass_success, ["t1"])
        self.assertEqual(result.fail_to_pass_success, ["t2"])
        self.assertEqual(result.backend, "swe-bench-live-native")

    def test_inspect_native_instance_file_reports_missing_fields(self) -> None:
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

            info = SWEBenchCodeExecutor.inspect_native_instance_file(instance_path)

            self.assertIn("patch", info["missing_fields"])
            self.assertIn("test_patch", info["missing_fields"])
            self.assertFalse(info["has_docker_image"])
            self.assertEqual(info["instance_id"], "native-1")

    def test_inspect_native_instance_file_inferrs_linux_from_x86_64_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_path = Path(tmp_dir) / "instance.json"
            instance_path.write_text(
                json.dumps(
                    {
                        "instance_id": "native-2",
                        "repo": "owner/repo",
                        "patch": "p",
                        "test_patch": "t",
                        "PASS_TO_PASS": [],
                        "FAIL_TO_PASS": [],
                        "test_cmds": ["pytest"],
                        "docker_image": "starryzhang/sweb.eval.x86_64.owner_1776_repo-456",
                    }
                ),
                encoding="utf-8",
            )

            info = SWEBenchCodeExecutor.inspect_native_instance_file(instance_path)

            self.assertEqual(info["platform_hint"], "linux")

    def test_build_prediction_payload_wraps_model_patch(self) -> None:
        payload = SWEBenchCodeExecutor.build_prediction_payload(
            {
                "instance_id": "swe-bridge",
                "pred_patch": "diff --git a/x b/x",
            }
        )
        self.assertEqual(payload["swe-bridge"]["model_patch"], "diff --git a/x b/x")

    def test_backend_name_for_instance_payload_is_native(self) -> None:
        self.assertEqual(
            SWEBenchCodeExecutor.backend_name_for_instance_payload(
                {
                    "instance_id": "local-1",
                    "repo": "repo",
                }
            ),
            "swe-bench-live-native",
        )

    @mock.patch("acbench.adapters.swebench.build_engine_for_instance")
    def test_run_single_instance_uses_internal_engine_contract(self, mock_engine_factory) -> None:
        engine = mock.Mock()
        engine.run.return_value = CodeRunOutcome(
            resolved=True,
            pass_to_pass_success=["t1"],
            fail_to_pass_success=["t2"],
            logs={"report_path": "report.json"},
        )
        mock_engine_factory.return_value = engine

        report = SWEBenchCodeExecutor._run_single_instance(
            {
                "instance_id": "native-1",
                "repo": "owner/repo",
                "platform": "linux",
                "patch": "p",
                "pred_patch": "pp",
                "test_patch": "tp",
                "PASS_TO_PASS": ["t1"],
                "FAIL_TO_PASS": ["t2"],
                "test_cmds": ["pytest"],
            },
            output_dir=Path("out"),
        )

        engine.run.assert_called_once()
        self.assertEqual(report["instance_id"], "native-1")
        self.assertTrue(report["resolved"])
        self.assertEqual(report["PASS_TO_PASS"]["success"], ["t1"])
        self.assertEqual(report["FAIL_TO_PASS"]["success"], ["t2"])


if __name__ == "__main__":
    unittest.main()
