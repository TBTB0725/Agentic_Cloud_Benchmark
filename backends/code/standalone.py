"""Standalone execution primitives for the future internal ACBench code backend."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess


def prepare_workspace(source_repo: str | Path, run_dir: str | Path) -> Path:
    """Copy a source repository into a run-local workspace."""

    repo_path = Path(source_repo)
    if not repo_path.is_absolute():
        repo_path = Path.cwd() / repo_path
    repo_path = repo_path.resolve()

    workspace_path = Path(run_dir) / "workspace"
    shutil.copytree(repo_path, workspace_path)
    return workspace_path


def run_commands(commands: list[str], repo_path: str | Path) -> tuple[bool, str]:
    """Run commands in one repository and aggregate logs."""

    if not commands:
        return True, ""

    target = Path(repo_path)
    chunks: list[str] = []
    overall_success = True
    for command in commands:
        result = run_single_command(command, target)
        chunks.append(
            f"$ {command}\n{result.stdout}{result.stderr}\nexit_code={result.returncode}\n"
        )
        if result.returncode != 0:
            overall_success = False
            break
    return overall_success, "\n".join(chunks)


def run_single_command(command: str, repo_path: Path) -> subprocess.CompletedProcess[str]:
    """Run one command in the repository path."""

    if os.name == "nt":
        return subprocess.run(
            ["powershell", "-Command", command],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    return subprocess.run(
        command,
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=True,
    )


def capture_git_diff(repo_path: str | Path) -> str:
    """Capture a git diff for one repository when possible."""

    target = Path(repo_path)
    if not shutil.which("git"):
        return ""
    result = subprocess.run(
        ["git", "--no-pager", "diff", "HEAD", "--text"],
        cwd=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def apply_patch(repo_path: str | Path, patch_file: str | Path) -> tuple[bool, str]:
    """Apply a unified diff patch to a repository."""

    target = Path(repo_path)
    patch_path = Path(patch_file)
    if not patch_path.exists():
        return False, f"Patch file does not exist: {patch_path}\n"
    if (target / ".git").exists() and shutil.which("git"):
        result = subprocess.run(
            [
                "git",
                "apply",
                "--reject",
                "--whitespace=nowarn",
                str(patch_path),
            ],
            cwd=target,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        output = (
            f"$ git apply --reject --whitespace=nowarn {patch_path}\n"
            f"{result.stdout}{result.stderr}\nexit_code={result.returncode}\n"
        )
        return result.returncode == 0, output
    return apply_patch_without_git(target, patch_path)


def apply_patch_without_git(repo_path: Path, patch_file: Path) -> tuple[bool, str]:
    """Apply a small unified diff patch without requiring git metadata."""

    patch_text = patch_file.read_text(encoding="utf-8")
    sections = _split_patch_sections(patch_text)
    applied_files: list[str] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.splitlines()
        if len(lines) < 3:
            return False, f"Unsupported patch section in {patch_file}\n"
        old_path, remaining_lines = _extract_patch_target(lines, patch_file)
        if not old_path:
            return False, f"Unsupported patch header in {patch_file}\n"
        target_rel = old_path[2:] if old_path.startswith("a/") else old_path
        target_file = repo_path / target_rel
        if not target_file.exists():
            return False, f"Target file does not exist for patch: {target_file}\n"

        original = target_file.read_text(encoding="utf-8").splitlines()
        hunks = parse_unified_hunks(remaining_lines, target_file)
        if isinstance(hunks, str):
            return False, hunks
        patched = list(original)
        search_start = 0
        for source_chunk, target_chunk in hunks:
            match_index = find_subsequence(patched, source_chunk, search_start)
            if match_index < 0:
                return False, f"Context mismatch while patching {target_file}\n"
            patched = (
                patched[:match_index]
                + target_chunk
                + patched[match_index + len(source_chunk) :]
            )
            search_start = match_index + len(target_chunk)
        target_file.write_text("\n".join(patched) + "\n", encoding="utf-8")
        applied_files.append(str(target_file))

    return True, "Applied patch without git to:\n" + "\n".join(applied_files) + "\n"


def _split_patch_sections(patch_text: str) -> list[str]:
    """Split a patch into per-file sections for git-style and plain unified diffs."""

    if "diff --git " in patch_text:
        return patch_text.split("diff --git ")
    if patch_text.lstrip().startswith("--- "):
        return [patch_text]
    return [patch_text]


def _extract_patch_target(lines: list[str], patch_file: Path) -> tuple[str, list[str]]:
    """Extract the target path and remaining hunk lines from one patch section."""

    first = lines[0]
    if first.startswith("--- "):
        old_path = first.split(maxsplit=1)[1]
        return old_path, lines

    header_parts = first.split()
    if len(header_parts) < 2:
        return "", lines
    old_path = header_parts[0]
    return old_path, lines[1:]


def parse_unified_hunks(
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


def find_subsequence(lines: list[str], chunk: list[str], start: int) -> int:
    """Find a sequence of lines inside a larger line list."""

    if not chunk:
        return start
    last = len(lines) - len(chunk) + 1
    for idx in range(start, max(last, start)):
        if lines[idx : idx + len(chunk)] == chunk:
            return idx
    return -1
