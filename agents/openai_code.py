"""OpenAI-backed code agent integrations for ACBench."""

from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

from acbench.models.runtime import RunConfig
from acbench.models.scenario import ScenarioSpec


class OpenAICodePatchAgent:
    """Generate a unified diff patch for a repository-backed code task."""

    def generate_patch(
        self,
        scenario: ScenarioSpec,
        run_config: RunConfig,
        *,
        output_dir: Path,
    ) -> dict[str, str]:
        repository_path = scenario.service.repository_path or ""
        if not repository_path:
            raise ValueError("OpenAICodePatchAgent requires a repository_path.")

        api_key = os.environ.get(run_config.openai_api_key_env or "OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                f"Environment variable `{run_config.openai_api_key_env}` is not set."
            )
        if not run_config.openai_model:
            raise ValueError("RunConfig.openai_model is required for OpenAICodePatchAgent.")

        repo_root = Path(repository_path)
        if not repo_root.is_absolute():
            repo_root = Path.cwd() / repo_root
        repo_root = repo_root.resolve()

        prompt = self._build_prompt(scenario, repo_root)
        client = OpenAI(
            api_key=api_key,
            base_url=run_config.openai_base_url or None,
        )
        response = client.responses.create(
            model=run_config.openai_model,
            input=prompt,
        )
        raw_text = getattr(response, "output_text", "") or ""
        patch_text = self._extract_patch(raw_text)

        prompt_path = output_dir / "openai_prompt.txt"
        response_path = output_dir / "openai_response.txt"
        patch_path = output_dir / "openai_generated_patch.diff"
        prompt_path.write_text(prompt, encoding="utf-8")
        response_path.write_text(raw_text, encoding="utf-8")
        patch_path.write_text(patch_text, encoding="utf-8")
        return {
            "patch_text": patch_text,
            "prompt_path": str(prompt_path),
            "response_path": str(response_path),
            "generated_patch_path": str(patch_path),
        }

    def _build_prompt(self, scenario: ScenarioSpec, repo_root: Path) -> str:
        target_files = list(scenario.code_fault.target_files if scenario.code_fault else [])
        if not target_files:
            target_files = self._discover_default_targets(repo_root)

        sections = [
            "You are fixing a repository-backed benchmark task.",
            "Return only a valid unified diff patch.",
            f"Scenario ID: {scenario.scenario_id}",
            f"Title: {scenario.title}",
            f"Notes: {scenario.notes}",
            f"Repository root: {repo_root}",
            "Rebuild commands:",
            *[f"- {command}" for command in scenario.build.rebuild_cmds],
            "Test commands:",
            *[f"- {command}" for command in scenario.build.test_cmds],
            "Target files and nearby test context:",
        ]
        for relative_path in target_files:
            file_path = repo_root / relative_path
            if not file_path.exists():
                continue
            sections.append(f"\n--- FILE: {relative_path} ---")
            sections.append(file_path.read_text(encoding="utf-8"))

        for test_path in self._discover_test_files(repo_root):
            sections.append(f"\n--- TEST: {test_path} ---")
            sections.append((repo_root / test_path).read_text(encoding="utf-8"))

        sections.append(
            "\nReturn only the patch. Do not include explanations, markdown fences, or prose."
        )
        return "\n".join(sections)

    @staticmethod
    def _discover_default_targets(repo_root: Path) -> list[str]:
        candidates = []
        for root_name in ("src",):
            root_dir = repo_root / root_name
            if root_dir.exists():
                for path in root_dir.rglob("*.py"):
                    candidates.append(str(path.relative_to(repo_root)).replace("\\", "/"))
        return candidates[:10]

    @staticmethod
    def _discover_test_files(repo_root: Path) -> list[str]:
        tests_dir = repo_root / "tests"
        if not tests_dir.exists():
            return []
        files = [
            str(path.relative_to(repo_root)).replace("\\", "/")
            for path in tests_dir.rglob("test_*.py")
        ]
        return files[:10]

    @staticmethod
    def _extract_patch(response_text: str) -> str:
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
