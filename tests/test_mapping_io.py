from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from controller_mapper.mapping_io import create_mapping, load_mapping, mapping_paths, render_markdown_report, sanitize_filename, save_mapping_files
from controller_mapper.models import DeviceInfo


class MappingIoTests(unittest.TestCase):
    def device(self) -> DeviceInfo:
        return DeviceInfo(
            name="Test Controller, Weird/Name",
            guid="03000000abcd",
            instance_id=7,
            axes=6,
            buttons=12,
            hats=1,
        )

    def test_sanitize_filename(self) -> None:
        self.assertEqual(sanitize_filename("  A/B:C*D  "), "A_B_C_D")
        self.assertEqual(sanitize_filename(""), "controller")

    def test_save_load_and_backup(self) -> None:
        mapping = create_mapping(
            device=self.device(),
            controls={"a": "b0", "leftx": "a0"},
            deadzone=0.15,
            capture_threshold=0.45,
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = save_mapping_files(mapping, tmp, write_sdl=True)
            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())
            self.assertTrue(paths["sdl"].exists())

            loaded = load_mapping(paths["json"])
            self.assertEqual(loaded["device"]["guid"], "03000000abcd")

            save_mapping_files(mapping, tmp)
            self.assertTrue(paths["json"].with_suffix(".json.bak").exists())
            self.assertTrue(paths["markdown"].with_suffix(".md.bak").exists())

    def test_mapping_paths_are_sanitized(self) -> None:
        paths = mapping_paths(Path("out"), self.device())
        self.assertEqual(paths["json"].name, "Test_Controller_Weird_Name_03000000abcd.json")

    def test_report_contains_controls(self) -> None:
        mapping = create_mapping(
            device=self.device(),
            controls={"a": "b0"},
            deadzone=0.15,
            capture_threshold=0.45,
        )
        report = render_markdown_report(mapping)
        self.assertIn("| `a` |", report)
        self.assertIn("SDL Mapping String", report)

    def test_json_is_utf8_and_sorted(self) -> None:
        mapping = create_mapping(
            device=self.device(),
            controls={"a": "b0"},
            deadzone=0.15,
            capture_threshold=0.45,
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = save_mapping_files(mapping, tmp)
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertEqual(parsed["controls"]["a"], "b0")


if __name__ == "__main__":
    unittest.main()
