from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from controller_mapper.capture import Candidate
from controller_mapper.gui_model import GuiState, VISUAL_CONTROLS, active_controls_for_state, control_at, load_mapping_for_gui, stick_values_for_display
from controller_mapper.mapping_io import load_mapping, save_mapping_files
from controller_mapper.models import DeviceInfo, RawState


class GuiModelTests(unittest.TestCase):
    def device(self) -> DeviceInfo:
        return DeviceInfo(
            name="Xbox 360 Controller",
            guid="030003f05e0400008e02000000007200",
            instance_id=0,
            axes=6,
            buttons=11,
            hats=1,
        )

    def test_click_target_enters_rebind_state(self) -> None:
        state = GuiState.from_device(self.device())

        state.begin_rebind("a")

        self.assertEqual(state.waiting_for, "a")
        self.assertIn("正在校准", state.status)

    def test_fake_button_candidate_rebinds_target_control(self) -> None:
        state = GuiState.from_device(self.device())
        state.begin_rebind("a")

        state.apply_candidate(Candidate(code="b0", score=1.0, kind="button"))

        self.assertIsNone(state.waiting_for)
        self.assertTrue(state.dirty)
        self.assertEqual(state.mapping["controls"]["a"], "b0")

    def test_fake_axis_candidate_records_axis_direction(self) -> None:
        state = GuiState.from_device(self.device())
        state.begin_rebind("leftx")

        state.apply_candidate(Candidate(code="a0", score=0.8, kind="axis", axis_value=-0.8))

        self.assertEqual(state.mapping["controls"]["leftx"], "a0")
        self.assertEqual(state.mapping["normalization"]["axis_directions"]["leftx"], -1)

    def test_active_controls_from_mapping_and_raw_state(self) -> None:
        mapping = {
            "controls": {
                "a": "b0",
                "leftx": "a0",
                "righttrigger": "+a1",
                "dpup": "h0.1",
            },
            "normalization": {
                "deadzone": 0.15,
                "capture_threshold": 0.45,
                "axis_directions": {},
                "trigger_ranges": {},
            },
        }
        raw_state = RawState(buttons=(True,), axes=(0.7, 0.6), hats=((0, 1),))

        active = active_controls_for_state(mapping, raw_state)

        self.assertTrue(active["a"])
        self.assertAlmostEqual(active["leftx"], 0.7)
        self.assertAlmostEqual(active["righttrigger"], 0.6)
        self.assertTrue(active["dpup"])

    def test_control_at_returns_visual_button_name(self) -> None:
        self.assertEqual(control_at((788, 436)), "a")
        self.assertEqual(control_at((298, 478)), "leftstick")
        self.assertEqual(control_at((658, 478)), "rightstick")
        self.assertIsNone(control_at((450, 265)))
        self.assertIsNone(control_at((520, 270)))
        self.assertIsNone(control_at((590, 265)))
        self.assertIsNone(control_at((40, 40)))

    def test_dpad_uses_arrow_labels(self) -> None:
        labels = {control.name: control.label for control in VISUAL_CONTROLS}
        self.assertEqual(labels["dpup"], "↑")
        self.assertEqual(labels["dpdown"], "↓")
        self.assertEqual(labels["dpleft"], "←")
        self.assertEqual(labels["dpright"], "→")

    def test_layout_positions_match_compact_panel(self) -> None:
        controls = {control.name: control.box for control in VISUAL_CONTROLS}
        self.assertEqual(controls["lefttrigger"].y, 214)
        self.assertEqual(controls["leftshoulder"].y, 258)
        self.assertEqual(controls["dpup"].x, 375)
        self.assertEqual(controls["y"].x, 760)

    def test_removed_labels_are_not_visible_controls(self) -> None:
        visible = {control.name for control in VISUAL_CONTROLS}
        self.assertNotIn("back", visible)
        self.assertNotIn("guide", visible)
        self.assertNotIn("start", visible)
        self.assertNotIn("leftx", visible)
        self.assertNotIn("lefty", visible)
        self.assertNotIn("rightx", visible)
        self.assertNotIn("righty", visible)

    def test_stick_display_falls_back_to_raw_axes_when_unmapped(self) -> None:
        mapping = {
            "controls": {
                "leftx": None,
                "lefty": None,
                "rightx": None,
                "righty": None,
            },
            "normalization": {
                "deadzone": 0.15,
                "capture_threshold": 0.45,
                "axis_directions": {},
                "trigger_ranges": {},
            },
        }
        raw_state = RawState(buttons=(), axes=(0.5, -0.25, 0.75, -0.9), hats=())

        values = stick_values_for_display(mapping, raw_state)

        self.assertEqual(values["leftx"], 0.5)
        self.assertEqual(values["lefty"], -0.25)
        self.assertEqual(values["rightx"], 0.75)
        self.assertEqual(values["righty"], -0.9)

    def test_save_mapping_files_for_gui_state(self) -> None:
        state = GuiState.from_device(self.device())
        state.begin_rebind("a")
        state.apply_candidate(Candidate(code="b0", score=1.0, kind="button"))

        with tempfile.TemporaryDirectory() as tmp:
            paths = save_mapping_files(state.mapping, tmp, write_sdl=True)

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())
            self.assertTrue(paths["sdl"].exists())
            self.assertEqual(load_mapping(paths["json"])["controls"]["a"], "b0")

    def test_load_mapping_for_gui_uses_existing_default_file(self) -> None:
        state = GuiState.from_device(self.device())
        state.begin_rebind("a")
        state.apply_candidate(Candidate(code="b0", score=1.0, kind="button"))

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            save_mapping_files(state.mapping, output_dir, write_sdl=True)

            mapping, path = load_mapping_for_gui(self.device(), mapping_file=None, output_dir=output_dir)

            self.assertIsNotNone(path)
            self.assertEqual(mapping["controls"]["a"], "b0")


if __name__ == "__main__":
    unittest.main()
