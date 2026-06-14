from __future__ import annotations

import os
import unittest

from controller_mapper.capture import MissingPygameError, _load_pygame
from controller_mapper.models import RawState
from controller_mapper.monitor import describe_input_code, diff_raw_states, format_all_state, hat_mask_name


class MonitorTests(unittest.TestCase):
    def test_diff_raw_states_reports_changed_inputs(self) -> None:
        previous = RawState(
            buttons=(False, True),
            axes=(0.0, -1.0),
            hats=((0, 0),),
        )
        current = RawState(
            buttons=(True, False),
            axes=(0.6, -0.98),
            hats=((0, 1),),
        )

        lines = diff_raw_states(previous, current, axis_threshold=0.05)

        self.assertIn("button 0 pressed", lines)
        self.assertIn("button 1 released", lines)
        self.assertIn("axis 0 = +0.00 -> +0.60", lines)
        self.assertIn("hat 0 = up", lines)
        self.assertNotIn("axis 1 = -1.00 -> -0.98", lines)

    def test_format_all_state(self) -> None:
        state = RawState(
            buttons=(True, False),
            axes=(0.0, -1.0),
            hats=((1, -1),),
        )

        lines = format_all_state(state)

        self.assertEqual(lines[0], "buttons: b0=1 b1=0")
        self.assertEqual(lines[1], "axes: a0=+0.00 a1=-1.00")
        self.assertEqual(lines[2], "hats: h0=right+down")

    def test_describe_input_code(self) -> None:
        self.assertEqual(describe_input_code("b0"), "第 0 号按钮")
        self.assertEqual(describe_input_code("a2"), "第 2 号轴")
        self.assertEqual(describe_input_code("+a3"), "第 3 号轴")
        self.assertEqual(describe_input_code("h0.1"), "hat/十字键输入 h0.1")

    def test_hat_mask_name(self) -> None:
        self.assertEqual(hat_mask_name(0), "center")
        self.assertEqual(hat_mask_name(1), "up")
        self.assertEqual(hat_mask_name(10), "right+left")

    def test_pygame_support_prompt_is_hidden_before_import(self) -> None:
        previous = os.environ.pop("PYGAME_HIDE_SUPPORT_PROMPT", None)
        try:
            try:
                _load_pygame()
            except MissingPygameError:
                pass
            self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")
        finally:
            if previous is None:
                os.environ.pop("PYGAME_HIDE_SUPPORT_PROMPT", None)
            else:
                os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = previous


if __name__ == "__main__":
    unittest.main()
