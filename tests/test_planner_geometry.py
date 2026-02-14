"""Tests for pure planner geometry helpers."""

from __future__ import annotations

import unittest

from planner.planner_geometry import (
    ascending_step_positions,
    compute_daily_view_geometry,
    compute_month_grid_geometry,
    compute_week_grid_geometry,
    daily_priorities_row_bounds,
    daily_schedule_row_bounds,
    month_cell_rect,
    month_day_badge_rect,
    month_weekday_label_center,
    week_column_rect,
    week_writing_line_y_positions,
)
from planner.profiles import DEFAULT_RENDER_PROFILE, resolve_render_profile


class MonthGeometryTests(unittest.TestCase):
    def test_month_geometry_uses_profile_dimensions(self) -> None:
        geometry = compute_month_grid_geometry(DEFAULT_RENDER_PROFILE)
        month_profile = DEFAULT_RENDER_PROFILE.layout.month

        self.assertEqual(
            geometry.start_x,
            DEFAULT_RENDER_PROFILE.sidebar_width + month_profile.side_padding,
        )
        self.assertEqual(
            geometry.start_y,
            DEFAULT_RENDER_PROFILE.page_height
            - DEFAULT_RENDER_PROFILE.header_height
            - month_profile.top_padding,
        )
        self.assertGreater(geometry.col_width, 0)
        self.assertGreater(geometry.row_height, 0)

    def test_month_cell_and_badge_geometry(self) -> None:
        geometry = compute_month_grid_geometry(DEFAULT_RENDER_PROFILE)
        cell = month_cell_rect(geometry, row_idx=1, col_idx=2)
        badge = month_day_badge_rect(
            cell,
            box_height=DEFAULT_RENDER_PROFILE.layout.month.day_number_box_height,
            box_max_width=DEFAULT_RENDER_PROFILE.layout.month.day_number_box_max_width,
        )
        center = month_weekday_label_center(geometry, col_idx=2)

        self.assertAlmostEqual(cell.x, geometry.start_x + (2 * geometry.col_width))
        self.assertAlmostEqual(cell.y, geometry.start_y - (2 * geometry.row_height))
        self.assertLessEqual(badge.width, cell.width)
        self.assertAlmostEqual(badge.top, cell.top)
        self.assertAlmostEqual(center.x, geometry.start_x + (2.5 * geometry.col_width))


class WeekGeometryTests(unittest.TestCase):
    def test_week_geometry_rejects_invalid_column_count(self) -> None:
        with self.assertRaises(ValueError):
            compute_week_grid_geometry(DEFAULT_RENDER_PROFILE, column_count=0)

    def test_week_writing_lines_stay_within_column(self) -> None:
        geometry = compute_week_grid_geometry(DEFAULT_RENDER_PROFILE, column_count=7)
        column = week_column_rect(geometry, col_idx=0)
        line_positions = week_writing_line_y_positions(geometry, column=column)

        self.assertTrue(line_positions)
        self.assertGreaterEqual(min(line_positions), column.y + geometry.writing_line_bottom_margin)
        self.assertLessEqual(max(line_positions), geometry.start_y - geometry.writing_line_top_offset)


class DailyGeometryTests(unittest.TestCase):
    def test_daily_geometry_uses_compact_profile_flags(self) -> None:
        compact_profile = resolve_render_profile(device="palma", layout="compact")
        geometry = compute_daily_view_geometry(compact_profile)

        self.assertFalse(geometry.show_schedule)
        self.assertFalse(geometry.show_priorities)
        self.assertGreater(geometry.notes_grid_step, 0)

    def test_daily_schedule_row_bounds_validation(self) -> None:
        geometry = compute_daily_view_geometry(DEFAULT_RENDER_PROFILE)
        with self.assertRaises(ValueError):
            daily_schedule_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            daily_schedule_row_bounds(geometry, geometry.schedule_hour_count)

    def test_daily_priorities_row_bounds_validation(self) -> None:
        geometry = compute_daily_view_geometry(DEFAULT_RENDER_PROFILE)
        with self.assertRaises(ValueError):
            daily_priorities_row_bounds(geometry, -1)
        with self.assertRaises(ValueError):
            daily_priorities_row_bounds(geometry, geometry.checklist_items)


class GeometryStepTests(unittest.TestCase):
    def test_ascending_step_positions_rejects_non_positive_step(self) -> None:
        with self.assertRaises(ValueError):
            ascending_step_positions(start=0, end=10, step=0)

    def test_ascending_step_positions_returns_interior_positions(self) -> None:
        self.assertEqual(
            ascending_step_positions(start=0, end=10, step=3),
            (3, 6, 9),
        )
