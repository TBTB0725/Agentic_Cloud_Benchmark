"""Tests for the minimal OpenAI-backed ops agent."""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from acbench.agents.openai_ops import OpenAIOpsAgent
from acbench.models.runtime import RunConfig


class _FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class _FakeClient:
    def __init__(self, output_text: str) -> None:
        self._output_text = output_text
        self.responses = self

    def create(self, **kwargs):
        return _FakeResponse(self._output_text)


class OpenAIOpsAgentTests(unittest.TestCase):
    def test_agent_configures_from_run_config(self) -> None:
        agent = OpenAIOpsAgent()
        agent.configure(
            RunConfig(
                openai_model="gpt-test",
                openai_api_key_env="TEST_OPENAI_KEY",
                openai_base_url="https://example.invalid/v1",
            )
        )
        self.assertEqual(agent.model, "gpt-test")
        self.assertEqual(agent.api_key_env, "TEST_OPENAI_KEY")
        self.assertEqual(agent.base_url, "https://example.invalid/v1")

    def test_agent_normalizes_yes_submission(self) -> None:
        agent = OpenAIOpsAgent()
        agent.configure(RunConfig(openai_model="gpt-test"))
        agent.init_context("problem", "instructions", {})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "acbench.agents.openai_ops.OpenAI",
                return_value=_FakeClient('submit("Yes")'),
            ):
                action = asyncio.run(agent.get_action("observation"))
        self.assertEqual(action, '```\nsubmit("Yes")\n```')

    def test_agent_normalizes_plain_no_response(self) -> None:
        agent = OpenAIOpsAgent()
        agent.configure(RunConfig(openai_model="gpt-test"))
        agent.init_context("problem", "instructions", {})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "acbench.agents.openai_ops.OpenAI",
                return_value=_FakeClient("No, this does not appear to be present."),
            ):
                action = asyncio.run(agent.get_action("observation"))
        self.assertEqual(action, '```\nsubmit("No")\n```')

    def test_agent_records_prompt_response_and_action(self) -> None:
        agent = OpenAIOpsAgent()
        agent.configure(RunConfig(openai_model="gpt-test"))
        agent.init_context("problem", "instructions", {})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "acbench.agents.openai_ops.OpenAI",
                return_value=_FakeClient('submit("Yes")'),
            ):
                action = asyncio.run(agent.get_action("observation"))
        self.assertEqual(action, '```\nsubmit("Yes")\n```')
        self.assertIn("Important detection rule", agent.last_prompt)
        self.assertEqual(agent.last_response, 'submit("Yes")')
        self.assertEqual(agent.last_action, '```\nsubmit("Yes")\n```')


if __name__ == "__main__":
    unittest.main()
