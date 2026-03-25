"""Tests for the local combined prototype path."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from acbench.models.runtime import RunConfig
from acbench.runner import ACBenchRunner


class CombinedLocalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="acbench-combined-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_combined_local_fixture_succeeds_with_gold_patch(self) -> None:
        runner = ACBenchRunner(root_dir=self.temp_dir)
        scenario_path = (
            Path(__file__).resolve().parents[1]
            / "scenarios"
            / "examples"
            / "combined_local_fixture.json"
        )
        patch_path = (
            Path(__file__).resolve().parents[1]
            / "patches"
            / "local_repo_buggy_fix.diff"
        )

        result = runner.run(
            scenario_path,
            dry_run=False,
            run_config=RunConfig(
                dry_run=False,
                code_patch_path=str(patch_path),
                max_steps=5,
            ),
        )

        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.ops_result)
        self.assertIsNotNone(result.code_result)
        self.assertTrue(result.ops_result.success)
        self.assertTrue(result.code_result.success)
