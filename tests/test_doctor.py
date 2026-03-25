"""Tests for environment diagnostics."""

from __future__ import annotations

import unittest

from acbench.doctor import (
    build_readiness_bundle,
    inspect_acbench_code_backend,
    inspect_aiopslab,
    inspect_swebench_live,
)
from acbench.external import aiopslab_root, swebench_live_root


class DoctorTests(unittest.TestCase):
    def test_aiopslab_doctor_exposes_environment_checks(self) -> None:
        report = inspect_aiopslab(aiopslab_root())
        self.assertIn("config_exists", report.extra_checks)
        self.assertIn("kubectl_current_context", report.extra_checks)
        self.assertIn("cluster_reachable", report.extra_checks)
        self.assertIn("helm_path", report.extra_checks)
        self.assertIn("helm_version", report.extra_checks)
        self.assertIsInstance(report.next_actions, list)

    def test_swebench_doctor_exposes_docker_daemon_check(self) -> None:
        report = inspect_swebench_live(swebench_live_root())
        self.assertEqual(report.extra_checks["backend_type"], "upstream-native")
        self.assertIn("docker_daemon_reachable", report.extra_checks)
        self.assertIn("docker_daemon_message", report.extra_checks)
        self.assertIn("docker_cli_reachable", report.extra_checks)
        self.assertIn("docker_cli_message", report.extra_checks)
        self.assertIsInstance(report.next_actions, list)

    def test_build_readiness_bundle_contains_summary(self) -> None:
        bundle = build_readiness_bundle(
            aiopslab_root=aiopslab_root(),
            swebench_root=swebench_live_root(),
        )
        self.assertIn("acbench_code", bundle)
        self.assertIn("swe_bench_live_native", bundle)
        self.assertIn("summary", bundle)
        self.assertIn("aiopslab_live_ready", bundle["summary"])
        self.assertIn("acbench_code_ready", bundle["summary"])
        self.assertIn("swe_bench_live_native_ready", bundle["summary"])

    def test_acbench_code_doctor_exposes_standalone_backend_checks(self) -> None:
        report = inspect_acbench_code_backend()
        self.assertEqual(report.name, "acbench-code")
        self.assertIn("backend_type", report.extra_checks)
        self.assertIn("git_available", report.extra_checks)
        self.assertIsInstance(report.next_actions, list)

    def test_aiopslab_next_actions_avoid_hardcoded_sibling_paths(self) -> None:
        report = inspect_aiopslab(aiopslab_root())
        for action in report.next_actions:
            self.assertNotIn("AIOpsLab/aiopslab/config.yml", action)
            self.assertNotIn("aiopslab/config.yml", action)


if __name__ == "__main__":
    unittest.main()
