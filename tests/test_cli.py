"""CLI-level tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from planner.main import main as planner_main


class TemplateDiscoveryCliTests(unittest.TestCase):
    def test_templates_list_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = planner_main(["templates", "list"])
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn("notes", text)
        self.assertIn("day-at-glance", text)

    def test_templates_show_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = planner_main(["templates", "show", "notes"])
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn("id: notes", text)
        self.assertIn("params:", text)
        self.assertIn("notes_fill", text)

    def test_templates_show_unknown_template_exits_with_cli_error(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as context:
                planner_main(["templates", "show", "unknown"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("error: unknown template 'unknown'", stderr.getvalue())


class TemplateParamCliTests(unittest.TestCase):
    def test_param_override_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "notes_grid.pdf"
            with redirect_stdout(io.StringIO()):
                status = planner_main(
                    [
                        "templates",
                        "generate",
                        "notes",
                        "--param",
                        "notes_fill=grid",
                        "--output",
                        str(output_path),
                    ]
                )
            self.assertEqual(status, 0)
            self.assertTrue(output_path.exists())

    def test_templates_generate_accepts_theme_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "notes_theme.pdf"
            theme_path = Path(tmp_dir) / "theme.json"
            theme_path.write_text(json.dumps({"accent": "#112233"}), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                status = planner_main(
                    [
                        "templates",
                        "generate",
                        "notes",
                        "--output",
                        str(output_path),
                        "--theme-file",
                        str(theme_path),
                    ]
                )
            self.assertEqual(status, 0)
            self.assertTrue(output_path.exists())

    def test_templates_generate_invalid_theme_file_exits_with_cli_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            theme_path = Path(tmp_dir) / "theme.json"
            theme_path.write_text(json.dumps({"unknown": "#111111"}), encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as context:
                    planner_main(
                        [
                            "templates",
                            "generate",
                            "notes",
                            "--theme-file",
                            str(theme_path),
                        ]
                    )

        self.assertEqual(context.exception.code, 2)
        self.assertIn("error: unknown theme key(s): unknown.", stderr.getvalue())
