"""Tests for internal ops engine helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from acbench.backends.ops.engine import (
    StandaloneLocalOpsEngine,
    UpstreamAIOpsLabEngine,
    build_default_engine,
    build_engine_for_problem,
)
from acbench.backends.ops.runtime import NativeOpsProblem, OpsRunRequest


class OpsEngineTests(unittest.TestCase):
    def test_standalone_local_ops_engine_returns_synthetic_outcome(self) -> None:
        engine = StandaloneLocalOpsEngine()
        with tempfile.TemporaryDirectory() as tmp_dir:
            outcome = engine.run(
                OpsRunRequest(
                    problem=NativeOpsProblem(
                        problem_id="p-1",
                        source="acbench",
                        application="app",
                        service="svc",
                        require_detection=True,
                        require_localization=True,
                        require_repair=False,
                    ),
                    output_dir=Path(tmp_dir),
                    max_steps=5,
                )
            )

        self.assertTrue(outcome.success)
        self.assertTrue(outcome.detected)
        self.assertTrue(outcome.localized)
        self.assertFalse(outcome.repaired)
        self.assertEqual(outcome.metrics["TTD"], 1.0)
        self.assertEqual(outcome.details["mode"], "synthetic-local-ops")

    def test_build_engine_for_problem_uses_standalone_for_acbench_source(self) -> None:
        engine = build_engine_for_problem(
            NativeOpsProblem(
                problem_id="p-1",
                source="acbench",
                application="app",
                service="svc",
            )
        )

        self.assertIsInstance(engine, StandaloneLocalOpsEngine)

    def test_build_default_engine_uses_upstream_aiopslab_placeholder(self) -> None:
        engine = build_default_engine()
        self.assertIsInstance(engine, UpstreamAIOpsLabEngine)


if __name__ == "__main__":
    unittest.main()
