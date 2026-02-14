"""Tests for rendering component validation."""

from __future__ import annotations

import unittest

from planner.components import (
    draw_breadcrumbs,
    draw_grid,
    draw_link_row,
    draw_sidebar,
    draw_week_grid,
)


class SidebarValidationTests(unittest.TestCase):
    def test_draw_sidebar_rejects_negative_active_month(self) -> None:
        with self.assertRaises(ValueError):
            draw_sidebar(None, -1)  # type: ignore[arg-type]

    def test_draw_sidebar_rejects_active_month_over_12(self) -> None:
        with self.assertRaises(ValueError):
            draw_sidebar(None, 13)  # type: ignore[arg-type]


class GridValidationTests(unittest.TestCase):
    def test_draw_grid_rejects_more_than_six_weeks(self) -> None:
        calendar_matrix = [[0, 0, 0, 0, 0, 0, 0] for _ in range(7)]
        with self.assertRaises(ValueError):
            draw_grid(None, calendar_matrix=calendar_matrix)  # type: ignore[arg-type]

    def test_draw_grid_rejects_weeks_with_wrong_day_count(self) -> None:
        calendar_matrix = [[1, 2, 3]]
        with self.assertRaises(ValueError):
            draw_grid(None, calendar_matrix=calendar_matrix)  # type: ignore[arg-type]

    def test_draw_week_grid_rejects_wrong_day_count(self) -> None:
        with self.assertRaises(ValueError):
            draw_week_grid(None, week=[1, 2, 3])  # type: ignore[arg-type]

    def test_draw_week_grid_rejects_empty_day_indexes(self) -> None:
        with self.assertRaises(ValueError):
            draw_week_grid(
                None,
                week=[1, 2, 3, 4, 5, 6, 7],
                day_indexes=[],
            )  # type: ignore[arg-type]

    def test_draw_week_grid_rejects_invalid_day_indexes(self) -> None:
        with self.assertRaises(ValueError):
            draw_week_grid(
                None,
                week=[1, 2, 3, 4, 5, 6, 7],
                day_indexes=[7],
            )  # type: ignore[arg-type]


class NavigationValidationTests(unittest.TestCase):
    def test_draw_breadcrumbs_rejects_empty_crumb_list(self) -> None:
        with self.assertRaises(ValueError):
            draw_breadcrumbs(None, [])  # type: ignore[arg-type]

    def test_draw_link_row_rejects_unknown_alignment(self) -> None:
        with self.assertRaises(ValueError):
            draw_link_row(None, [("A", "Dest")], y=100, align="middle")  # type: ignore[arg-type]
