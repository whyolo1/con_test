from __future__ import annotations

import unittest

from controller_mapper.sdl import build_sdl_mapping, hat_to_mask, parse_input_code


class SdlTests(unittest.TestCase):
    def test_parse_input_codes(self) -> None:
        self.assertEqual(parse_input_code("b3").kind, "button")
        axis = parse_input_code("~+a2")
        self.assertEqual(axis.kind, "axis")
        self.assertTrue(axis.inverted)
        self.assertEqual(axis.half, "+")
        hat = parse_input_code("h0.8")
        self.assertEqual(hat.kind, "hat")
        self.assertEqual(hat.hat_mask, 8)

    def test_hat_to_mask(self) -> None:
        self.assertEqual(hat_to_mask((0, 1)), 1)
        self.assertEqual(hat_to_mask((1, 0)), 2)
        self.assertEqual(hat_to_mask((0, -1)), 4)
        self.assertEqual(hat_to_mask((-1, 0)), 8)

    def test_build_sdl_mapping(self) -> None:
        mapping = {
            "device": {"guid": "03000000abcd", "name": "Pad, One"},
            "controls": {
                "a": "b0",
                "b": "b1",
                "leftx": "a0",
                "lefty": "a1",
                "dpup": "h0.1",
            },
            "normalization": {
                "axis_directions": {"lefty": -1},
            },
        }
        text = build_sdl_mapping(mapping, platform="Windows")
        self.assertTrue(text.startswith("03000000abcd,Pad  One,"))
        self.assertIn("a:b0", text)
        self.assertIn("lefty:~a1", text)
        self.assertIn("dpup:h0.1", text)
        self.assertTrue(text.endswith("platform:Windows,"))

    def test_guid_required(self) -> None:
        with self.assertRaises(ValueError):
            build_sdl_mapping({"device": {"name": "No Guid"}, "controls": {}})


if __name__ == "__main__":
    unittest.main()
