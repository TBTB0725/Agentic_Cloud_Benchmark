"""Tests for the internal ACBench code runtime engine layer."""

from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from acbench.backends.code.engine import (
    StandaloneLocalEngine,
    UpstreamSWEBenchEngine,
    build_default_engine,
    build_engine_for_instance,
)
from acbench.backends.code.runtime import CodeRunRequest, NativeCodeInstance


class CodeEngineTests(unittest.TestCase):
    @mock.patch.object(UpstreamSWEBenchEngine, "_run_upstream_instance")
    def test_upstream_engine_converts_report_into_code_outcome(self, mock_run) -> None:
        mock_run.return_value = {
            "instance_id": "native-1",
            "resolved": True,
            "PASS_TO_PASS": {"success": ["t1"], "failure": []},
            "FAIL_TO_PASS": {"success": ["t2"], "failure": []},
            "logs": {"report_path": "report.json"},
        }
        engine = UpstreamSWEBenchEngine(repo_root=Path("C:/repo"))
        outcome = engine.run(
            CodeRunRequest(
                instance=NativeCodeInstance(
                    instance_id="native-1",
                    repo="owner/repo",
                    platform="linux",
                    patch="p",
                    pred_patch="pp",
                    test_patch="tp",
                    pass_to_pass=["t1"],
                    fail_to_pass=["t2"],
                ),
                output_dir=Path("out"),
            )
        )

        self.assertTrue(outcome.resolved)
        self.assertEqual(outcome.pass_to_pass_success, ["t1"])
        self.assertEqual(outcome.fail_to_pass_success, ["t2"])
        self.assertEqual(outcome.logs["report_path"], "report.json")

    def test_build_default_engine_returns_upstream_bridge(self) -> None:
        engine = build_default_engine()
        self.assertIsInstance(engine, UpstreamSWEBenchEngine)

    def test_build_engine_for_instance_uses_standalone_for_local_repo(self) -> None:
        with mock.patch("pathlib.Path.exists", return_value=True):
            engine = build_engine_for_instance(
                NativeCodeInstance(
                    instance_id="local-1",
                    repo="C:/repo",
                    platform="windows",
                    patch="p",
                    pred_patch="pp",
                    test_patch="tp",
                )
            )
        self.assertIsInstance(engine, StandaloneLocalEngine)

    def test_build_engine_for_instance_keeps_upstream_for_native_docker_case(self) -> None:
        engine = build_engine_for_instance(
            NativeCodeInstance(
                instance_id="native-1",
                repo="owner/repo",
                platform="linux",
                patch="p",
                pred_patch="pp",
                test_patch="tp",
                docker_image="example/native:latest",
            )
        )
        self.assertIsInstance(engine, UpstreamSWEBenchEngine)


if __name__ == "__main__":
    unittest.main()
