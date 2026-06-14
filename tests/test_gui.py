from __future__ import annotations

import unittest

from controller_mapper.gui import _darken, _shift_box
from controller_mapper.gui_model import HitBox


class GuiDrawingTests(unittest.TestCase):
    def test_shift_box_moves_pressed_button_down(self) -> None:
        box = HitBox(10, 20, 30, 40)

        shifted = _shift_box(box, dy=2)

        self.assertEqual(shifted.x, 10)
        self.assertEqual(shifted.y, 22)
        self.assertEqual(shifted.width, 30)
        self.assertEqual(shifted.height, 40)

    def test_darken_clamps_channels(self) -> None:
        self.assertEqual(_darken((20, 40, 80), 30), (0, 10, 50))


if __name__ == "__main__":
    unittest.main()
