"""Tests for API-backed standalone code execution hooks."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from acbench.executors.standalone_code import StandaloneCodeExecutor
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


class FakePatchAgent:
    """Return the known-good patch for the local buggy fixture."""

    def generate_patch(self, scenario, run_config, *, output_dir):
        patch_path = Path(__file__).resolve().parents[1] / "patches" / "local_repo_buggy_fix.diff"
        patch_text = patch_path.read_text(encoding="utf-8")
        generated_patch_path = output_dir / "fake_agent_patch.diff"
        generated_patch_path.write_text(patch_text, encoding="utf-8")
        return {
            "patch_text": patch_text,
            "generated_patch_path": str(generated_patch_path),
        }


class StandaloneCodeExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="acbench-standalone-executor-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_executor_can_use_agent_generated_patch(self) -> None:
        scenario = ScenarioSpec.from_file(
            Path(__file__).resolve().parents[1]
            / "scenarios"
            / "examples"
            / "code_only_local_repo_buggy.json"
        )
        executor = StandaloneCodeExecutor()

        result = executor.execute(
            scenario=scenario,
            run_dir=self.temp_dir / "run",
            run_config=RunConfig(
                code_agent_ref="acbench.tests.test_standalone_code_executor:FakePatchAgent",
                openai_model="test-model",
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.backend, "acbench-code-standalone")
        self.assertIn("generated_patch_path", result.logs)
        self.assertTrue(Path(result.logs["generated_patch_path"]).exists())


if __name__ == "__main__":
    unittest.main()
