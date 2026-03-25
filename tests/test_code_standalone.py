"""Tests for standalone code execution primitives."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from acbench.backends.code.standalone import (
    apply_patch_without_git,
    capture_git_diff,
    find_subsequence,
    parse_unified_hunks,
    prepare_workspace,
    run_commands,
)


class CodeStandaloneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="acbench-standalone-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_prepare_workspace_copies_repository(self) -> None:
        repo_dir = self.temp_dir / "repo"
        run_dir = self.temp_dir / "run"
        repo_dir.mkdir(parents=True, exist_ok=True)
        run_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "sample.txt").write_text("hello\n", encoding="utf-8")

        workspace = prepare_workspace(repo_dir, run_dir)

        self.assertTrue((workspace / "sample.txt").exists())
        self.assertEqual((workspace / "sample.txt").read_text(encoding="utf-8"), "hello\n")

    def test_run_commands_aggregates_output(self) -> None:
        ok, output = run_commands(['Write-Output "ok"'], self.temp_dir)
        self.assertTrue(ok)
        self.assertIn("ok", output)

    def test_apply_patch_without_git_updates_file(self) -> None:
        repo_dir = self.temp_dir / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        target = repo_dir / "sample.txt"
        target.write_text("before\n", encoding="utf-8")
        patch = self.temp_dir / "sample.diff"
        patch.write_text(
            "\n".join(
                [
                    "diff --git a/sample.txt b/sample.txt",
                    "--- a/sample.txt",
                    "+++ b/sample.txt",
                    "@@ -1 +1 @@",
                    "-before",
                    "+after",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        success, output = apply_patch_without_git(repo_dir, patch)

        self.assertTrue(success)
        self.assertIn("Applied patch without git", output)
        self.assertEqual(target.read_text(encoding="utf-8"), "after\n")

    def test_apply_patch_without_git_accepts_plain_unified_diff(self) -> None:
        repo_dir = self.temp_dir / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        target = repo_dir / "sample.txt"
        target.write_text("before\n", encoding="utf-8")
        patch = self.temp_dir / "sample.diff"
        patch.write_text(
            "\n".join(
                [
                    "--- a/sample.txt",
                    "+++ b/sample.txt",
                    "@@ -1 +1 @@",
                    "-before",
                    "+after",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        success, output = apply_patch_without_git(repo_dir, patch)

        self.assertTrue(success)
        self.assertIn("Applied patch without git", output)
        self.assertEqual(target.read_text(encoding="utf-8"), "after\n")

    def test_parse_unified_hunks_extracts_source_and_target(self) -> None:
        hunks = parse_unified_hunks(
            [
                "--- a/sample.txt",
                "+++ b/sample.txt",
                "@@ -1 +1 @@",
                "-before",
                "+after",
            ],
            Path("sample.txt"),
        )
        self.assertEqual(hunks, [(["before"], ["after"])])

    def test_find_subsequence_returns_match_index(self) -> None:
        index = find_subsequence(["a", "b", "c"], ["b", "c"], 0)
        self.assertEqual(index, 1)

    def test_capture_git_diff_returns_empty_without_git_repo(self) -> None:
        repo_dir = self.temp_dir / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "sample.txt").write_text("hello\n", encoding="utf-8")
        self.assertEqual(capture_git_diff(repo_dir), "")


if __name__ == "__main__":
    unittest.main()
