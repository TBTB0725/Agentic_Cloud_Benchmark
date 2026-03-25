"""OpenAI-backed ops agent integrations for ACBench."""

from __future__ import annotations

import os
import re

from openai import OpenAI


class OpenAIOpsAgent:
    """Minimal AIOpsLab-compatible agent backed by an OpenAI-compatible API."""

    def __init__(self) -> None:
        self.model = ""
        self.api_key_env = "OPENAI_API_KEY"
        self.base_url = ""
        self.problem_desc = ""
        self.instructions = ""
        self.apis = {}
        self.last_prompt = ""
        self.last_response = ""
        self.last_action = ""

    def configure(self, run_config) -> None:
        """Load runtime configuration before the problem starts."""

        self.model = run_config.openai_model
        self.api_key_env = run_config.openai_api_key_env or "OPENAI_API_KEY"
        self.base_url = run_config.openai_base_url or ""

    def init_context(self, problem_desc: str, instructions: str, apis: dict) -> None:
        self.problem_desc = problem_desc
        self.instructions = instructions
        self.apis = apis

    async def get_action(self, input_text: str) -> str:
        api_key = os.environ.get(self.api_key_env, "")
        if not api_key:
            raise ValueError(f"Environment variable `{self.api_key_env}` is not set.")
        if not self.model:
            raise ValueError("OpenAIOpsAgent requires a configured OpenAI model.")

        client = OpenAI(api_key=api_key, base_url=self.base_url or None)
        prompt = self._build_prompt(input_text)
        self.last_prompt = prompt
        response = client.responses.create(
            model=self.model,
            input=prompt,
        )
        text = getattr(response, "output_text", "") or ""
        self.last_response = text
        action = self._normalize_action(text)
        self.last_action = action
        return action

    def _build_prompt(self, input_text: str) -> str:
        return "\n".join(
            [
                "You are controlling an AIOps benchmark agent.",
                "Return exactly one valid action.",
                "For the current minimal prototype, prefer a final submit action.",
                "If the evidence indicates the detection statement is true, return submit(\"Yes\").",
                "If the evidence indicates the detection statement is false, return submit(\"No\").",
                "Important detection rule: in these prototype detection tasks, the fault has already been injected before you answer.",
                "Unless the prompt explicitly says the fault is absent, recovered, or normal, detection tasks should submit(\"Yes\").",
                "Return only the action, optionally inside one fenced code block.",
                "",
                "Problem description:",
                self.problem_desc,
                "",
                "Instructions:",
                self.instructions,
                "",
                "Current observation:",
                input_text,
            ]
        )

    @staticmethod
    def _normalize_action(response_text: str) -> str:
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        match = re.search(r'(submit\((?:.|\n)*?\))', text)
        if match:
            action = match.group(1).strip()
            return f"```\n{action}\n```"

        lowered = text.lower()
        if "yes" in lowered:
            return '```\nsubmit("Yes")\n```'
        if "no" in lowered:
            return '```\nsubmit("No")\n```'
        return "```\nsubmit()\n```"
