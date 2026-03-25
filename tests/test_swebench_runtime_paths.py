"""Tests for SWE-bench-Live runtime path handling."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SWE_ROOT = REPO_ROOT / "SWE-bench-Live"
LAUNCH_ROOT = SWE_ROOT / "launch"

for candidate in (str(SWE_ROOT), str(LAUNCH_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from launch.core.runtime import SetupRuntime  # noqa: E402


class SWEBenchRuntimePathTests(unittest.TestCase):
    def test_linux_bind_path_uses_forward_slashes(self) -> None:
        bind_path = SetupRuntime._container_bind_path("/testbed", "linux")
        self.assertEqual(bind_path, "/testbed/mnt_tmp")

    def test_windows_bind_path_uses_backslashes(self) -> None:
        bind_path = SetupRuntime._container_bind_path(r"C:\testbed", "windows")
        self.assertEqual(bind_path, r"C:\testbed\mnt_tmp")


if __name__ == "__main__":
    unittest.main()
