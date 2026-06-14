from __future__ import annotations

import unittest

from controller_mapper.normalize import normalize_state


class NormalizeTests(unittest.TestCase):
    def test_normalizes_buttons_axes_triggers_and_hats(self) -> None:
        mapping = {
            "controls": {
                "a": "b0",
                "b": "b1",
                "leftx": "a0",
                "lefty": "a1",
                "lefttrigger": "a2",
                "righttrigger": "b2",
                "dpup": "h0.1",
                "dpright": "+a3",
            },
            "normalization": {
                "deadzone": 0.15,
                "capture_threshold": 0.45,
                "axis_directions": {"lefty": -1},
                "trigger_ranges": {"lefttrigger": {"released": -1.0, "pressed": 1.0}},
            },
        }
        raw = {
            "buttons": [True, False, True],
            "axes": [0.6, -0.7, 0.0, 0.8],
            "hats": [(0, 1)],
        }

        normalized = normalize_state(raw, mapping)

        self.assertTrue(normalized["a"])
        self.assertFalse(normalized["b"])
        self.assertAlmostEqual(normalized["leftx"], 0.6)
        self.assertAlmostEqual(normalized["lefty"], 0.7)
        self.assertAlmostEqual(normalized["lefttrigger"], 0.5)
        self.assertAlmostEqual(normalized["righttrigger"], 1.0)
        self.assertTrue(normalized["dpup"])
        self.assertTrue(normalized["dpright"])

    def test_deadzone_zeroes_small_axis_values(self) -> None:
        mapping = {
            "controls": {"leftx": "a0"},
            "normalization": {"deadzone": 0.2, "axis_directions": {}, "trigger_ranges": {}},
        }
        normalized = normalize_state({"buttons": [], "axes": [0.1], "hats": []}, mapping)
        self.assertEqual(normalized["leftx"], 0.0)

    def test_missing_inputs_are_safe(self) -> None:
        mapping = {
            "controls": {"a": "b4", "leftx": "a9", "dpup": "h2.1"},
            "normalization": {},
        }
        normalized = normalize_state({"buttons": [], "axes": [], "hats": []}, mapping)
        self.assertFalse(normalized["a"])
        self.assertEqual(normalized["leftx"], 0.0)
        self.assertFalse(normalized["dpup"])


if __name__ == "__main__":
    unittest.main()
