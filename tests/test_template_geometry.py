"""Tests for pure template geometry helpers."""

from __future__ import annotations

import unittest

from planner.profiles import DEVICE_PROFILES
from planner.template_geometry import (
    ascending_step_positions,
    checklist_row_bounds,
    compact_priorities_row_bounds,
    compact_schedule_row_bounds,
    compute_checklist_geometry,
    compute_day_at_glance_compact_geometry,
    compute_day_at_glance_geometry,
    compute_schedule_geometry,
    day_at_glance_priorities_row_bounds,
    day_at_glance_schedule_row_bounds,
    descending_step_positions,
    schedule_row_bounds,
)
from planner.template_layout import (
    content_bounds,
    mm_to_device_units,
    pt_to_device_units,
    resolve_template_layout,
)


class StepPositionTests(unittest.TestCase):
    def test_ascending_positions_include_start_and_end(self) -> None:
        self.assertEqual(
            ascending_step_positions(start=0, end=10, step=5, include_start=True, include_end=True),
            (0, 5, 10),
        )

    def test_descending_positions_reject_non_positive_step(self) -> None:
        with self.assertRaises(ValueError):
            descending_step_positions(start=10, end=0, step=0)


class ScheduleGeometryTests(unittest.TestCase):
    def test_schedule_geometry_includes_highlight_within_body(self) -> None:
        device = DEVICE_PROFILES["remarkable"]
        layout = resolve_template_layout(device="remarkable", layout="balanced")
        left, bottom, right, top = content_bounds(device, layout)
        header_bottom = top - mm_to_device_units(layout.header_height_mm, device=device)

        geometry = compute_schedule_geometry(
            device=device,
            layout=layout,
            left=left,
            bottom=bottom,
            right=right,
            header_bottom=header_bottom,
            work_start_hour=9,
            work_end_hour=18,
        )

        expected_rows = (layout.schedule_end_hour - layout.schedule_start_hour) + 1
        self.assertEqual(len(geometry.hours), expected_rows)
        highlight = geometry.highlight_rect
        self.assertIsNotNone(highlight)
        if highlight is None:
            self.fail("expected schedule highlight geometry")
        self.assertGreaterEqual(highlight.y, geometry.body.y)
        self.assertLessEqual(highlight.top, geometry.body.top)

    def test_schedule_row_bounds_validation(self) -> None:
        device = DEVICE_PROFILES["remarkable"]
        layout = resolve_template_layout(device="remarkable", layout="balanced")
        left, bottom, right, top = content_bounds(device, layout)
        header_bottom = top - mm_to_device_units(layout.header_height_mm, device=device)
        geometry = compute_schedule_geometry(
            device=device,
            layout=layout,
            left=left,
            bottom=bottom,
            right=right,
            header_bottom=header_bottom,
            work_start_hour=9,
            work_end_hour=18,
        )

        with self.assertRaises(ValueError):
            schedule_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            schedule_row_bounds(geometry, len(geometry.hours))


class DayAtGlanceGeometryTests(unittest.TestCase):
    def test_full_day_at_glance_row_bounds_validation(self) -> None:
        device = DEVICE_PROFILES["remarkable"]
        layout = resolve_template_layout(device="remarkable", layout="balanced")
        left, bottom, right, top = content_bounds(device, layout)
        header_bottom = top - mm_to_device_units(layout.header_height_mm, device=device)
        geometry = compute_day_at_glance_geometry(
            device=device,
            layout=layout,
            left=left,
            bottom=bottom,
            right=right,
            header_bottom=header_bottom,
        )

        with self.assertRaises(ValueError):
            day_at_glance_schedule_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            day_at_glance_schedule_row_bounds(geometry, geometry.hour_count)

        with self.assertRaises(ValueError):
            day_at_glance_priorities_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            day_at_glance_priorities_row_bounds(geometry, geometry.priorities_rows)

    def test_compact_geometry_adjusts_schedule_for_notes_minimum(self) -> None:
        device = DEVICE_PROFILES["remarkable"]
        layout = resolve_template_layout(device="remarkable", layout="balanced")

        content_height = 740.0
        geometry = compute_day_at_glance_compact_geometry(
            device=device,
            layout=layout,
            left=0.0,
            bottom=0.0,
            right=900.0,
            header_bottom=content_height,
        )

        min_notes_height = pt_to_device_units(110, device=device)
        notes_height = geometry.notes_top - geometry.notes_bottom
        self.assertAlmostEqual(notes_height, min_notes_height)

    def test_compact_row_bounds_validation(self) -> None:
        device = DEVICE_PROFILES["remarkable"]
        layout = resolve_template_layout(device="remarkable", layout="balanced")
        left, bottom, right, top = content_bounds(device, layout)
        header_bottom = top - mm_to_device_units(layout.header_height_mm, device=device)
        geometry = compute_day_at_glance_compact_geometry(
            device=device,
            layout=layout,
            left=left,
            bottom=bottom,
            right=right,
            header_bottom=header_bottom,
        )

        with self.assertRaises(ValueError):
            compact_priorities_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            compact_priorities_row_bounds(geometry, geometry.priorities_rows)

        with self.assertRaises(ValueError):
            compact_schedule_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            compact_schedule_row_bounds(geometry, len(geometry.schedule_hours))


class ChecklistGeometryTests(unittest.TestCase):
    def test_checklist_row_bounds_validation(self) -> None:
        device = DEVICE_PROFILES["remarkable"]
        layout = resolve_template_layout(device="remarkable", layout="balanced")
        left, bottom, right, top = content_bounds(device, layout)
        header_bottom = top - mm_to_device_units(layout.header_height_mm, device=device)
        geometry = compute_checklist_geometry(
            device=device,
            layout=layout,
            left=left,
            bottom=bottom,
            right=right,
            header_bottom=header_bottom,
        )

        with self.assertRaises(ValueError):
            checklist_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            checklist_row_bounds(geometry, geometry.rows)
