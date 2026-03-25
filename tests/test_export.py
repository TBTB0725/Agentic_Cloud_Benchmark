"""Tests for export and extraction helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from acbench.export import (
    _hf_cache_home,
    create_native_swebench_scenario,
    export_swebench_instance,
    extract_swebench_hf_instance,
    extract_swebench_jsonl_instance,
    list_swebench_hf_candidates,
    scaffold_native_swebench_bundle,
    scaffold_native_swebench_hf_bundle,
)


class ExportTests(unittest.TestCase):
    def test_export_swebench_instance_uses_standalone_payload_for_repo_backed_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir()
            output_path = Path(tmp_dir) / "instance.json"
            scenario_path = Path(tmp_dir) / "scenario.json"
            patch_path = Path(tmp_dir) / "fix.diff"
            patch_path.write_text("diff --git a/x b/x\n", encoding="utf-8")
            scenario_path.write_text(
                json.dumps(
                    {
                        "scenario_id": "repo-backed-swe-style",
                        "title": "repo backed",
                        "mode": "code_only",
                        "service": {
                            "application": "app",
                            "service": "svc",
                            "repository_path": str(repo_dir),
                        },
                        "code_fault": {
                            "source": "swe-bench-live",
                            "defect_id": "d1",
                        },
                        "build": {
                            "rebuild_cmds": ["build"],
                            "test_cmds": ["test"],
                        },
                        "gold_patch_path": str(patch_path),
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch("acbench.export.ACBenchRunner.run") as mock_run:
                mock_run.return_value.code_result = mock.Mock(
                    pass_to_pass_success=["t1"],
                    fail_to_pass_success=["t2"],
                )
                instance = export_swebench_instance(
                    scenario_path=scenario_path,
                    output_path=output_path,
                )

            self.assertEqual(instance["repo"], str(repo_dir))
            self.assertEqual(instance["rebuild_cmds"], ["build"])
            self.assertEqual(instance["PASS_TO_PASS"], ["t1"])
            self.assertEqual(instance["FAIL_TO_PASS"], ["t2"])
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["instance_id"], "repo-backed-swe-style")

    def test_extract_swebench_jsonl_instance_writes_selected_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.jsonl"
            output_path = Path(tmp_dir) / "instance.json"
            dataset_path.write_text(
                "\n".join(
                    [
                        json.dumps({"instance_id": "a-1", "repo": "owner/a"}),
                        json.dumps({"instance_id": "b-2", "repo": "owner/b"}),
                    ]
                ),
                encoding="utf-8",
            )

            record = extract_swebench_jsonl_instance(
                dataset_path=dataset_path,
                instance_id="b-2",
                output_path=output_path,
            )

            self.assertEqual(record["instance_id"], "b-2")
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["repo"], "owner/b")

    def test_create_native_swebench_scenario_from_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_path = Path(tmp_dir) / "instance.json"
            output_path = Path(tmp_dir) / "scenario.json"
            instance_path.write_text(
                json.dumps(
                    {
                        "instance_id": "owner__repo-123",
                        "repo": "owner/repo",
                        "docker_image": "example/native:linux",
                    }
                ),
                encoding="utf-8",
            )

            scenario = create_native_swebench_scenario(
                instance_path=instance_path,
                output_path=output_path,
            )

            self.assertEqual(scenario["scenario_id"], "swebench_native_owner__repo-123")
            self.assertEqual(scenario["service"]["service"], "repo")
            self.assertEqual(scenario["code_fault"]["platform"], "linux")
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["code_fault"]["instance_path"], str(instance_path))

    def test_create_native_swebench_scenario_inferrs_linux_from_x86_64_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_path = Path(tmp_dir) / "instance.json"
            output_path = Path(tmp_dir) / "scenario.json"
            instance_path.write_text(
                json.dumps(
                    {
                        "instance_id": "owner__repo-456",
                        "repo": "owner/repo",
                        "docker_image": "starryzhang/sweb.eval.x86_64.owner_1776_repo-456",
                    }
                ),
                encoding="utf-8",
            )

            scenario = create_native_swebench_scenario(
                instance_path=instance_path,
                output_path=output_path,
            )

            self.assertEqual(scenario["code_fault"]["platform"], "linux")

    def test_scaffold_native_swebench_bundle_creates_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_path = Path(tmp_dir) / "dataset.jsonl"
            output_dir = Path(tmp_dir) / "bundle"
            dataset_path.write_text(
                json.dumps({"instance_id": "b-2", "repo": "owner/b", "docker_image": "example/native:linux"}),
                encoding="utf-8",
            )

            bundle = scaffold_native_swebench_bundle(
                dataset_path=dataset_path,
                instance_id="b-2",
                output_dir=output_dir,
            )

            self.assertTrue(Path(bundle["instance_path"]).exists())
            self.assertTrue(Path(bundle["scenario_path"]).exists())

    @mock.patch("datasets.load_dataset")
    def test_extract_swebench_hf_instance_uses_workspace_cache(self, mock_load_dataset) -> None:
        mock_load_dataset.return_value = [{"instance_id": "hf-1", "repo": "owner/repo", "patch": "p", "test_patch": "t", "PASS_TO_PASS": [], "FAIL_TO_PASS": [], "test_cmds": ["pytest"]}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "hf-instance.json"

            record = extract_swebench_hf_instance(
                dataset_name="SWE-bench-Live/MultiLang",
                instance_id="hf-1",
                output_path=output_path,
                split="rust",
            )

            self.assertEqual(record["instance_id"], "hf-1")
            self.assertTrue(output_path.exists())
            self.assertEqual(os.environ["HF_HOME"], str(_hf_cache_home()))

    @mock.patch("acbench.export.extract_swebench_hf_instance")
    def test_scaffold_native_swebench_hf_bundle_creates_both_files(self, mock_extract_hf) -> None:
        def _write_instance(*, output_path, **_: object) -> dict:
            Path(output_path).write_text(
                json.dumps({"instance_id": "hf-2", "repo": "owner/repo", "docker_image": "example/native:linux"}),
                encoding="utf-8",
            )
            return {"instance_id": "hf-2"}

        mock_extract_hf.side_effect = _write_instance
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle = scaffold_native_swebench_hf_bundle(
                dataset_name="SWE-bench-Live/MultiLang",
                instance_id="hf-2",
                output_dir=tmp_dir,
                split="rust",
            )

            self.assertTrue(Path(bundle["instance_path"]).exists())
            self.assertTrue(Path(bundle["scenario_path"]).exists())

    @mock.patch("datasets.load_dataset")
    def test_list_swebench_hf_candidates_filters_and_marks_ready(self, mock_load_dataset) -> None:
        mock_load_dataset.return_value = [
            {
                "instance_id": "hf-ready",
                "repo": "owner/repo",
                "patch": "p",
                "test_patch": "tp",
                "PASS_TO_PASS": [],
                "FAIL_TO_PASS": [],
                "test_cmds": ["pytest"],
                "docker_image": "example/native:linux",
                "base_commit": "abc123",
            },
            {
                "instance_id": "hf-missing-image",
                "repo": "owner/repo2",
                "patch": "p",
                "test_patch": "tp",
                "PASS_TO_PASS": [],
                "FAIL_TO_PASS": [],
                "test_cmds": ["pytest"],
            },
        ]

        candidates = list_swebench_hf_candidates(
            dataset_name="SWE-bench-Live/MultiLang",
            split="rust",
            limit=10,
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["instance_id"], "hf-ready")
        self.assertTrue(candidates[0]["ready"])
        self.assertEqual(candidates[0]["platform_hint"], "linux")


if __name__ == "__main__":
    unittest.main()
