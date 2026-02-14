"""Tests for single-page template generation."""

from __future__ import annotations

import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from reportlab.pdfgen import canvas as reportlab_canvas

import planner.templates as templates_module
from planner.profiles import DEVICE_PROFILES
from planner.templates import (
    NOTES_FILL_TYPES,
    TEMPLATE_TYPES,
    available_template_types,
    generate_template,
    get_template_spec,
    list_template_specs,
    resolve_template_layout,
)
from planner.templates import font_pt_to_device_units, mm_to_device_units, pt_to_device_units

_PDF_PAGE_PATTERN = re.compile(rb"/Type\s*/Page\b")


class GenerateTemplateTests(unittest.TestCase):
    def test_generate_template_writes_single_page_pdf_for_each_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for template in TEMPLATE_TYPES:
                output_path = Path(tmp_dir) / f"{template}.pdf"
                generated_path = generate_template(template=template, output_path=output_path)

                self.assertEqual(generated_path, output_path)
                self.assertTrue(output_path.exists())

                data = output_path.read_bytes()
                self.assertTrue(data.startswith(b"%PDF"))
                self.assertEqual(len(_PDF_PAGE_PATTERN.findall(data)), 1)

    def test_generate_template_supports_device_and_layout_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "palma_grid.pdf"
            generated_path = generate_template(
                template="grid",
                output_path=output_path,
                device="palma",
                layout="compact",
                param_overrides={
                    "margin_mm": 6.5,
                    "header_height_mm": 6.0,
                    "grid_spacing_mm": 3.8,
                },
            )

            self.assertEqual(generated_path, output_path)
            self.assertTrue(output_path.exists())
            data = output_path.read_bytes()
            self.assertTrue(data.startswith(b"%PDF"))
            self.assertEqual(len(_PDF_PAGE_PATTERN.findall(data)), 1)

    def test_generate_notes_template_supports_all_fill_styles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for notes_fill in NOTES_FILL_TYPES:
                output_path = Path(tmp_dir) / f"notes_{notes_fill}.pdf"
                generated_path = generate_template(
                    template="notes",
                    output_path=output_path,
                    param_overrides={"notes_fill": notes_fill},
                )

                self.assertEqual(generated_path, output_path)
                self.assertTrue(output_path.exists())
                self.assertEqual(len(_PDF_PAGE_PATTERN.findall(output_path.read_bytes())), 1)

    def test_generate_template_rejects_unknown_template_or_layout(self) -> None:
        with self.assertRaises(ValueError):
            generate_template(template="unknown")
        with self.assertRaises(ValueError):
            generate_template(template="lines", layout="unknown")
        with self.assertRaises(ValueError):
            generate_template(template="lines", device="unknown")

    def test_generate_template_rejects_invalid_layout_parameters(self) -> None:
        with self.assertRaises(ValueError):
            generate_template(template="lines", param_overrides={"margin_mm": 0})
        with self.assertRaises(ValueError):
            generate_template(template="dotted-grid", param_overrides={"dot_radius_mm": 0})
        with self.assertRaises(ValueError):
            generate_template(
                template="day-at-glance",
                param_overrides={
                    "schedule_start_hour": 21,
                    "schedule_end_hour": 21,
                },
            )
        with self.assertRaises(ValueError):
            generate_template(template="task-list", param_overrides={"checklist_rows": 0})
        with self.assertRaises(ValueError):
            generate_template(template="todo-list", param_overrides={"checklist_rows": 0})
        with self.assertRaises(ValueError):
            generate_template(template="notes", param_overrides={"notes_fill": "unknown"})

    def test_generate_template_supports_todo_list_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_path = Path(tmp_dir) / "task_list.pdf"
            todo_path = Path(tmp_dir) / "todo_list.pdf"
            generate_template(template="task-list", output_path=task_path)
            generate_template(template="todo-list", output_path=todo_path)

            self.assertTrue(task_path.exists())
            self.assertTrue(todo_path.exists())
            self.assertEqual(len(_PDF_PAGE_PATTERN.findall(task_path.read_bytes())), 1)
            self.assertEqual(len(_PDF_PAGE_PATTERN.findall(todo_path.read_bytes())), 1)

    def test_generate_template_supports_local_plugin_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_dir = Path(tmp_dir) / "plugins"
            plugin_dir.mkdir(parents=True)
            plugin_file = plugin_dir / "demo_template_plugin.py"
            plugin_file.write_text(
                """
from planner.config import Theme
from planner.template_blocks import CompositeBlock, PageBackgroundBlock
from planner.template_engine import TemplateSpec

def _build(params):
    return CompositeBlock(blocks=(PageBackgroundBlock(color=Theme.BACKGROUND),))

def register_templates(registry):
    registry.register(
        TemplateSpec(
            template_id="plugin-blank",
            title="Plugin Blank",
            description="Plugin-provided blank page.",
            build=_build,
        )
    )
"""
            )

            sys.path.insert(0, str(plugin_dir))
            try:
                output_path = Path(tmp_dir) / "plugin_blank.pdf"
                generated_path = generate_template(
                    template="plugin-blank",
                    output_path=output_path,
                    plugin_modules=("demo_template_plugin",),
                )
                self.assertEqual(generated_path, output_path)
                self.assertTrue(output_path.exists())
                self.assertEqual(len(_PDF_PAGE_PATTERN.findall(output_path.read_bytes())), 1)
            finally:
                sys.path.remove(str(plugin_dir))
                sys.modules.pop("demo_template_plugin", None)

    def test_generate_template_emits_plugin_warning_before_unknown_template_error(self) -> None:
        missing_module = "_planner_missing_template_plugin_"
        sys.modules.pop(missing_module, None)

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaisesRegex(ValueError, "unknown template 'plugin-blank'"):
                generate_template(template="plugin-blank", plugin_modules=(missing_module,))

        warning_text = stderr.getvalue()
        self.assertIn(f"warning: failed to load template plugin '{missing_module}'", warning_text)

    def test_generate_schedule_template_defaults_to_extended_hours_on_palma(self) -> None:
        captured: dict[str, object] = {}
        original_renderer = templates_module.TEMPLATE_RENDERERS["schedule"]

        def capture_renderer(pdf: object, *, device: object, layout: object, theme: object) -> None:
            captured["layout"] = layout

        templates_module.TEMPLATE_RENDERERS["schedule"] = capture_renderer
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_template(
                    template="schedule",
                    output_path=Path(tmp_dir) / "schedule.pdf",
                    device="palma",
                )
        finally:
            templates_module.TEMPLATE_RENDERERS["schedule"] = original_renderer

        layout = captured["layout"]
        self.assertEqual(layout.schedule_start_hour, 6)
        self.assertEqual(layout.schedule_end_hour, 22)

    def test_schedule_template_includes_end_hour_label(self) -> None:
        labels: list[str] = []
        original_draw_centred_string = reportlab_canvas.Canvas.drawCentredString

        def capture_draw_centred_string(
            self: reportlab_canvas.Canvas,
            x: float,
            y: float,
            text: str,
            *args: object,
            **kwargs: object,
        ) -> None:
            labels.append(text)
            original_draw_centred_string(self, x, y, text, *args, **kwargs)

        reportlab_canvas.Canvas.drawCentredString = capture_draw_centred_string
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_template(
                    template="schedule",
                    output_path=Path(tmp_dir) / "schedule.pdf",
                    param_overrides={
                        "schedule_start_hour": 6,
                        "schedule_end_hour": 22,
                    },
                )
        finally:
            reportlab_canvas.Canvas.drawCentredString = original_draw_centred_string

        hour_labels = {label for label in labels if label.isdigit() and len(label) == 2}
        self.assertIn("22", hour_labels)


class TemplateLayoutResolutionTests(unittest.TestCase):
    def test_device_default_layout_is_applied(self) -> None:
        self.assertEqual(resolve_template_layout(device="remarkable").name, "balanced")
        self.assertEqual(resolve_template_layout(device="scribe").name, "full")
        self.assertEqual(resolve_template_layout(device="palma").name, "compact")
        palma_layout = resolve_template_layout(device="palma")
        self.assertEqual(palma_layout.margin_mm, 3.0)
        self.assertEqual(palma_layout.schedule_start_hour, 9)
        self.assertEqual(palma_layout.schedule_end_hour, 19)

    def test_mm_conversion_is_device_aware(self) -> None:
        self.assertAlmostEqual(
            mm_to_device_units(25.4, device=DEVICE_PROFILES["remarkable"]),
            226.0,
            places=6,
        )
        self.assertAlmostEqual(
            mm_to_device_units(25.4, device=DEVICE_PROFILES["scribe"]),
            300.0,
            places=6,
        )
        self.assertAlmostEqual(
            mm_to_device_units(25.4, device=DEVICE_PROFILES["palma"]),
            300.0,
            places=6,
        )

    def test_point_conversion_is_device_aware(self) -> None:
        self.assertAlmostEqual(
            pt_to_device_units(72.0, device=DEVICE_PROFILES["remarkable"]),
            226.0,
            places=6,
        )
        self.assertAlmostEqual(
            pt_to_device_units(72.0, device=DEVICE_PROFILES["scribe"]),
            300.0,
            places=6,
        )

    def test_font_point_conversion_applies_device_scale(self) -> None:
        self.assertAlmostEqual(
            font_pt_to_device_units(72.0, device=DEVICE_PROFILES["remarkable"]),
            226.0,
            places=6,
        )
        self.assertAlmostEqual(
            font_pt_to_device_units(72.0, device=DEVICE_PROFILES["palma"]),
            225.0,
            places=6,
        )


class TemplateRegistryApiTests(unittest.TestCase):
    def test_list_template_specs_matches_template_types(self) -> None:
        listed_ids = tuple(spec.template_id for spec in list_template_specs())
        self.assertEqual(listed_ids, TEMPLATE_TYPES)
        self.assertEqual(available_template_types(), TEMPLATE_TYPES)

    def test_get_template_spec_returns_notes_spec(self) -> None:
        spec = get_template_spec("notes")
        self.assertEqual(spec.template_id, "notes")
        self.assertEqual(spec.title, "Notes")
