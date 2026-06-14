from __future__ import annotations

import unittest

from controller_mapper.cli import build_parser


class CliTests(unittest.TestCase):
    def test_gui_command_arguments(self) -> None:
        parser = build_parser()

        args = parser.parse_args(
            [
                "gui",
                "--device",
                "0",
                "--mapping",
                "mappings/example.json",
                "--output-dir",
                "out",
            ]
        )

        self.assertEqual(args.device, 0)
        self.assertEqual(args.mapping, "mappings/example.json")
        self.assertEqual(args.output_dir, "out")
        self.assertTrue(callable(args.func))


if __name__ == "__main__":
    unittest.main()
