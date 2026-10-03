import importlib.util
from datetime import datetime
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "cast.py"
SPEC = importlib.util.spec_from_file_location("meihua_cast", MODULE_PATH)
CAST = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = CAST
SPEC.loader.exec_module(CAST)


class CastTests(unittest.TestCase):
    def test_two_number_zero_remainders(self):
        self.assertEqual(CAST.cast_two_numbers(8, 16), (8, 8, 6))

    def test_three_number_cast(self):
        self.assertEqual(CAST.cast_three_numbers(3, 6, 8), (3, 6, 2))

    def test_supplied_known_hexagram(self):
        result = CAST.compute(6, 3, 4)
        self.assertEqual(result["primary"]["name"], "水火既济")
        self.assertEqual(result["transformed"]["name"], "泽火革")
        self.assertEqual(result["body"]["name"], "离")
        self.assertEqual(result["function"]["name"], "坎")
        self.assertEqual(result["five_element_relation"], "用克体")

    def test_mutual_hexagram(self):
        result = CAST.compute(6, 3, 4)
        self.assertEqual(result["mutual"]["name"], "火水未济")

    def test_gregorian_time_is_deterministic_within_shichen(self):
        first = CAST.cast_gregorian_time(datetime.fromisoformat("2026-07-20T19:00:00+08:00"))
        second = CAST.cast_gregorian_time(datetime.fromisoformat("2026-07-20T20:59:00+08:00"))
        self.assertEqual(first, second)

    def test_all_64_hexagrams_named(self):
        names = {CAST.compute(upper, lower, 1)["primary"]["name"] for upper in range(1, 9) for lower in range(1, 9)}
        self.assertEqual(len(names), 64)


if __name__ == "__main__":
    unittest.main()
