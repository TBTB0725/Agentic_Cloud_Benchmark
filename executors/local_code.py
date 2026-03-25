"""Local command-based code executor for the ACBench prototype."""

from __future__ import annotations

from pathlib import Path
import re

from acbench.agents.loader import load_object
from acbench.backends.code.standalone import (
    apply_patch,
    capture_git_diff,
    prepare_workspace,
    run_commands,
    run_single_command,
)
from acbench.executors.base import BenchmarkExecutor
from acbench.models.result import ExecutorResult
from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


class LocalCodeExecutor(BenchmarkExecutor):
    """Execute rebuild and test commands directly in a local repository."""

    def __init__(self) -> None:
        super().__init__(backend_name="acbench-local-code")

    def execute(
        self,
        scenario: ScenarioSpec,
        run_dir: Path,
        run_config: RunConfig,
    ) -> ExecutorResult:
        repo_path = Path(scenario.service.repository_path or "")
        if not repo_path.is_absolute():
            repo_path = Path.cwd() / repo_path
        repo_path = repo_path.resolve()
        workspace_path = prepare_workspace(repo_path, run_dir)

        pre_patch_log_path = run_dir / "pre_patch_test.log"
        build_log_path = run_dir / "build.log"
        test_log_path = run_dir / "test.log"
        patch_path = run_dir / "patch.diff"
        apply_log_path = run_dir / "apply_patch.log"

        pre_test_success, pre_test_output = self._run_commands(
            scenario.build.test_cmds,
            workspace_path,
        )
        pre_patch_log_path.write_text(pre_test_output, encoding="utf-8")
        pre_status = self._parse_unittest_output(pre_test_output)

        applied_patch = ""
        apply_success = True
        patch_file_path = self._resolve_patch_file(
            scenario=scenario,
            run_config=run_config,
            run_dir=run_dir,
        )
        if patch_file_path:
            patch_file = patch_file_path
            if not patch_file.is_absolute():
                patch_file = Path.cwd() / patch_file
            patch_file = patch_file.resolve()
            apply_success, applied_patch = self._apply_patch(workspace_path, patch_file)
            apply_log_path.write_text(applied_patch, encoding="utf-8")

        build_success, build_output = self._run_commands(
            scenario.build.rebuild_cmds,
            workspace_path,
        ) if apply_success else (False, "")
        test_success, test_output = self._run_commands(
            scenario.build.test_cmds,
            workspace_path,
        ) if apply_success else (False, "")
        post_status = self._parse_unittest_output(test_output)
        pass_to_pass, fail_to_pass, pass_to_pass_failure, fail_to_pass_failure = self._compare_statuses(
            pre_status,
            post_status,
        )
        patch_output = self._capture_git_diff(workspace_path)
        if not patch_output and run_config.code_patch_path:
            patch_output = Path(run_config.code_patch_path).read_text(encoding="utf-8")

        build_log_path.write_text(build_output, encoding="utf-8")
        test_log_path.write_text(test_output, encoding="utf-8")
        patch_path.write_text(patch_output, encoding="utf-8")

        repaired = build_success and test_success
        success = True
        if scenario.success_criteria.require_build_success and not build_success:
            success = False
        if scenario.success_criteria.require_test_success and not test_success:
            success = False
        if scenario.success_criteria.require_repair and not repaired:
            success = False

        return ExecutorResult(
            backend=self.backend_name,
            success=success,
            repaired=repaired,
            build_success=build_success,
            test_success=test_success,
            pass_to_pass_success=pass_to_pass,
            pass_to_pass_failure=pass_to_pass_failure,
            fail_to_pass_success=fail_to_pass,
            fail_to_pass_failure=fail_to_pass_failure,
            metrics={
                "rebuild_cmd_count": len(scenario.build.rebuild_cmds),
                "test_cmd_count": len(scenario.build.test_cmds),
                "pre_test_success": pre_test_success,
                "post_test_success": test_success,
                "pre_test_cases": len(pre_status),
                "post_test_cases": len(post_status),
            },
            logs={
                "apply_log_path": str(apply_log_path) if patch_file_path else "",
                "pre_patch_test_log_path": str(pre_patch_log_path),
                "build_log_path": str(build_log_path),
                "test_log_path": str(test_log_path),
                "patch_path": str(patch_path),
            },
            details={
                "repository_path": str(repo_path),
                "workspace_path": str(workspace_path),
                "max_steps": run_config.max_steps,
                "apply_success": apply_success,
                "code_patch_path": str(patch_file_path) if patch_file_path else "",
                "pre_patch_status": pre_status,
                "post_patch_status": post_status,
            },
        )

    @staticmethod
    def _resolve_patch_file(
        scenario: ScenarioSpec,
        run_config: RunConfig,
        run_dir: Path,
    ) -> Path | None:
        if run_config.code_patch_path:
            return Path(run_config.code_patch_path)
        if not run_config.code_agent_ref:
            return None

        agent_cls = load_object(run_config.code_agent_ref)
        agent = agent_cls()
        if not hasattr(agent, "generate_patch"):
            raise ValueError(
                f"Configured code agent `{run_config.code_agent_ref}` does not expose `generate_patch`."
            )
        agent_artifacts = agent.generate_patch(
            scenario=scenario,
            run_config=run_config,
            output_dir=run_dir,
        )
        generated_patch_path = agent_artifacts.get("generated_patch_path", "")
        if generated_patch_path:
            return Path(generated_patch_path)
        patch_text = agent_artifacts.get("patch_text", "")
        if not patch_text:
            return None
        patch_path = run_dir / "agent_generated_patch.diff"
        patch_path.write_text(patch_text, encoding="utf-8")
        return patch_path

    def _run_commands(self, commands: list[str], repo_path: Path) -> tuple[bool, str]:
        """Run a list of commands and aggregate their output."""

        return run_commands(commands, repo_path)

    @staticmethod
    def _run_single_command(command: str, repo_path: Path):
        """Run one command in the local repository."""

        return run_single_command(command, repo_path)

    @staticmethod
    def _capture_git_diff(repo_path: Path) -> str:
        """Capture the local git diff if the repository is under git."""

        return capture_git_diff(repo_path)

    @staticmethod
    def _apply_patch(repo_path: Path, patch_file: Path) -> tuple[bool, str]:
        """Apply a unified diff patch to the local repository."""

        return apply_patch(repo_path, patch_file)

    @staticmethod
    def _apply_patch_without_git(repo_path: Path, patch_file: Path) -> tuple[bool, str]:
        """Apply a small unified diff patch without requiring a git repository."""

        patch_text = patch_file.read_text(encoding="utf-8")
        sections = patch_text.split("diff --git ")
        applied_files: list[str] = []

        for section in sections:
            section = section.strip()
            if not section:
                continue
            lines = section.splitlines()
            if len(lines) < 4:
                return False, f"Unsupported patch section in {patch_file}\n"

            header_parts = lines[0].split()
            if len(header_parts) < 2:
                return False, f"Unsupported patch header in {patch_file}\n"
            old_path = header_parts[0]
            target_rel = old_path[2:] if old_path.startswith("a/") else old_path
            target_file = repo_path / target_rel
            if not target_file.exists():
                return False, f"Target file does not exist for patch: {target_file}\n"

            original = target_file.read_text(encoding="utf-8").splitlines()
            hunks = LocalCodeExecutor._parse_unified_hunks(lines[1:], target_file)
            if isinstance(hunks, str):
                return False, hunks
            patched = list(original)
            search_start = 0
            for source_chunk, target_chunk in hunks:
                match_index = LocalCodeExecutor._find_subsequence(
                    patched,
                    source_chunk,
                    search_start,
                )
                if match_index < 0:
                    return False, f"Context mismatch while patching {target_file}\n"
                patched = (
                    patched[:match_index]
                    + target_chunk
                    + patched[match_index + len(source_chunk):]
                )
                search_start = match_index + len(target_chunk)
            target_file.write_text("\n".join(patched) + "\n", encoding="utf-8")
            applied_files.append(str(target_file))

        return True, "Applied patch without git to:\n" + "\n".join(applied_files) + "\n"

    @staticmethod
    def _parse_unified_hunks(
        lines: list[str],
        target_file: Path,
    ) -> list[tuple[list[str], list[str]]] | str:
        """Parse unified diff hunks into source and target chunks."""

        hunks: list[tuple[list[str], list[str]]] = []
        current_source: list[str] = []
        current_target: list[str] = []
        in_hunk = False

        for line in lines:
            if line.startswith(("index ", "--- ", "+++ ")):
                continue
            if line.startswith("@@"):
                if in_hunk:
                    hunks.append((current_source, current_target))
                if not re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line):
                    return f"Unsupported hunk header while patching {target_file}\n"
                current_source = []
                current_target = []
                in_hunk = True
                continue
            if not in_hunk:
                continue
            if line.startswith(" "):
                current_source.append(line[1:])
                current_target.append(line[1:])
            elif line.startswith("-"):
                current_source.append(line[1:])
            elif line.startswith("+"):
                current_target.append(line[1:])
            else:
                return f"Unsupported patch line while patching {target_file}: {line}\n"

        if in_hunk:
            hunks.append((current_source, current_target))
        return hunks

    @staticmethod
    def _find_subsequence(lines: list[str], chunk: list[str], start: int) -> int:
        """Find a sequence of lines inside a larger line list."""

        if not chunk:
            return start
        last = len(lines) - len(chunk) + 1
        for idx in range(start, max(last, start)):
            if lines[idx : idx + len(chunk)] == chunk:
                return idx
        return -1

    @staticmethod
    def _parse_unittest_output(output: str) -> dict[str, str]:
        """Parse minimal unittest results into pass/fail status per test case."""

        statuses: dict[str, str] = {}
        for line in output.splitlines():
            stripped = line.strip()
            match = re.match(r"^(test\w+.*)\s+\((.+)\)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped.*)$", stripped)
            if not match:
                continue
            test_name = f"{match.group(2)}::{match.group(1)}"
            raw_status = match.group(3).lower()
            if raw_status.startswith("ok"):
                statuses[test_name] = "pass"
            elif raw_status.startswith("skip"):
                statuses[test_name] = "skip"
            else:
                statuses[test_name] = "fail"
        return statuses

    @staticmethod
    def _compare_statuses(
        pre_status: dict[str, str],
        post_status: dict[str, str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Compute minimal PASS_TO_PASS and FAIL_TO_PASS summaries."""

        all_tests = set(pre_status) | set(post_status)
        pass_to_pass_success: list[str] = []
        fail_to_pass_success: list[str] = []
        pass_to_pass_failure: list[str] = []
        fail_to_pass_failure: list[str] = []

        for test_name in sorted(all_tests):
            before = pre_status.get(test_name, "skip")
            after = post_status.get(test_name, "skip")
            if before == "pass":
                if after == "pass":
                    pass_to_pass_success.append(test_name)
                else:
                    pass_to_pass_failure.append(test_name)
            elif before == "fail":
                if after == "pass":
                    fail_to_pass_success.append(test_name)
                else:
                    fail_to_pass_failure.append(test_name)
        return (
            pass_to_pass_success,
            fail_to_pass_success,
            pass_to_pass_failure,
            fail_to_pass_failure,
        )
