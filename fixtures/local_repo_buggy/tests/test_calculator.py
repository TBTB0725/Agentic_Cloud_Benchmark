"""Tests for the local ACBench calculator fixture."""

import unittest

from samplepkg.calculator import add


class CalculatorTests(unittest.TestCase):
    def test_addition_simple(self) -> None:
        self.assertEqual(add(2, 3), 5)

    def test_addition_with_zero(self) -> None:
        self.assertEqual(add(7, 0), 7)


if __name__ == "__main__":
    unittest.main()
