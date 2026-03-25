"""Tests for CLI utility output contracts."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from acbench.cli import run_doctor


class CLITests(unittest.TestCase):
    def test_run_doctor_reports_split_code_backends(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            result = run_doctor()

        payload = json.loads(stream.getvalue())
        self.assertEqual(result, 0)
        self.assertIn("aiopslab", payload)
        self.assertIn("acbench_code", payload)
        self.assertIn("swe_bench_live_native", payload)
        self.assertEqual(
            payload["acbench_code"]["extra_checks"]["backend_type"],
            "standalone-local-code",
        )
        self.assertEqual(
            payload["swe_bench_live_native"]["extra_checks"]["backend_type"],
            "upstream-native",
        )


if __name__ == "__main__":
    unittest.main()
