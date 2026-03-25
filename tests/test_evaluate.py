"""Tests for batch prediction evaluation."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from acbench.evaluate import evaluate_predictions


class EvaluateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="acbench-eval-"))
        self.output_path = self.temp_dir / "results.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_local_gold_manifest_evaluation(self) -> None:
        results = evaluate_predictions(
            manifest_path=Path("acbench/manifests/local_suite.json"),
            predictions_path=Path("acbench/predictions/local_gold.json"),
            output_path=self.output_path,
        )

        self.assertEqual(results["submitted"], 2)
        self.assertEqual(results["success"], 2)
        self.assertTrue(self.output_path.exists())
        payload = json.loads(self.output_path.read_text(encoding="utf-8"))
        self.assertIn("code_only_local_repo_buggy", payload["results"])
        self.assertIn("combined_local_fixture", payload["results"])
