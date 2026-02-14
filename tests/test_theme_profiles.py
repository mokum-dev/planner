"""Tests for theme profile resolution and validation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reportlab.lib import colors

from planner.theme_profiles import available_theme_profiles, resolve_theme


class ThemeProfileTests(unittest.TestCase):
    def test_available_theme_profiles_contains_default(self) -> None:
        self.assertIn("default", available_theme_profiles())

    def test_resolve_theme_defaults_match_builtin_theme_values(self) -> None:
        theme = resolve_theme()
        self.assertEqual(theme.FONT_HEADER, "Helvetica-Bold")
        self.assertEqual(theme.ACCENT.rgb(), colors.HexColor("#E67E22").rgb())

    def test_resolve_theme_applies_json_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            theme_path = Path(tmp_dir) / "theme.json"
            theme_path.write_text(
                json.dumps(
                    {
                        "accent": "#112233",
                        "font_header": "Courier-Bold",
                    }
                ),
                encoding="utf-8",
            )

            theme = resolve_theme(theme_file=theme_path)
            self.assertEqual(theme.ACCENT.rgb(), colors.HexColor("#112233").rgb())
            self.assertEqual(theme.FONT_HEADER, "Courier-Bold")

    def test_resolve_theme_rejects_unknown_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            theme_path = Path(tmp_dir) / "theme.json"
            theme_path.write_text(json.dumps({"unknown": "#111111"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unknown theme key\\(s\\): unknown"):
                resolve_theme(theme_file=theme_path)

    def test_resolve_theme_rejects_invalid_color(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            theme_path = Path(tmp_dir) / "theme.json"
            theme_path.write_text(json.dumps({"accent": "invalid-color"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid color value 'invalid-color'"):
                resolve_theme(theme_file=theme_path)
