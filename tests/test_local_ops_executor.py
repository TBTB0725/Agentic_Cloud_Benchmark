"""Tests for the local synthetic ops executor."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from acbench.executors.local_ops import LocalOpsExecutor
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


class LocalOpsExecutorTests(unittest.TestCase):
    def test_local_ops_executor_uses_internal_ops_runtime_contract(self) -> None:
        scenario = ScenarioSpec.from_dict(
            {
                "scenario_id": "local-ops-test",
                "title": "local ops",
                "mode": "ops_only",
                "service": {
                    "application": "app",
                    "service": "svc",
                },
                "ops_fault": {
                    "source": "acbench",
                    "problem_id": "p-1",
                    "description": "synthetic ops fault",
                },
                "success_criteria": {
                    "require_detection": True,
                    "require_localization": True,
                    "require_repair": False,
                },
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = LocalOpsExecutor().execute(
                scenario=scenario,
                run_dir=Path(tmp_dir),
                run_config=RunConfig(dry_run=False, max_steps=5),
            )

            self.assertIn("trace_path", result.logs)
            self.assertTrue(Path(result.logs["trace_path"]).exists())

        self.assertEqual(result.backend, "acbench-local-ops")
        self.assertTrue(result.success)
        self.assertTrue(result.detected)
        self.assertTrue(result.localized)
        self.assertFalse(result.repaired)
        self.assertTrue(result.metrics["synthetic"])
        self.assertEqual(result.details["mode"], "synthetic-local-ops")


if __name__ == "__main__":
    unittest.main()
