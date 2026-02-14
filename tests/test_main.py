"""Tests for planner generation."""

from __future__ import annotations

import calendar
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

from planner.main import (
    day_bookmark,
    expected_page_count,
    generate_planner,
    month_bookmark,
    month_matrix,
    week_bookmark,
)

_PDF_PAGE_PATTERN = re.compile(rb"/Type\s*/Page\b")
_PDF_LINK_PATTERN = re.compile(rb"/Subtype /Link")


class MonthMatrixTests(unittest.TestCase):
    def test_month_matrix_has_seven_days_per_week(self) -> None:
        matrix = month_matrix(2026, 2)
        self.assertGreaterEqual(len(matrix), 4)
        self.assertLessEqual(len(matrix), 6)
        self.assertTrue(all(len(week) == 7 for week in matrix))

    def test_month_matrix_rejects_invalid_month(self) -> None:
        with self.assertRaises(ValueError):
            month_matrix(2026, 0)
        with self.assertRaises(ValueError):
            month_matrix(2026, 13)


class GeneratePlannerTests(unittest.TestCase):
    def test_generate_planner_rejects_invalid_year(self) -> None:
        with self.assertRaises(ValueError):
            generate_planner(year=0, output_path=Path("unused.pdf"))
        with self.assertRaises(TypeError):
            generate_planner(year="2026", output_path=Path("unused.pdf"))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            generate_planner(year=True, output_path=Path("unused.pdf"))  # type: ignore[arg-type]

    def test_generate_planner_writes_pdf_with_month_week_day_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "planner.pdf"
            generated_path = generate_planner(year=2026, output_path=output_path)

            self.assertEqual(generated_path, output_path)
            self.assertTrue(output_path.exists())

            data = output_path.read_bytes()
            self.assertTrue(data.startswith(b"%PDF"))
            self.assertEqual(len(_PDF_PAGE_PATTERN.findall(data)), expected_page_count(2026))
            self.assertIn(b"Week 01", data)
            self.assertGreater(len(_PDF_LINK_PATTERN.findall(data)), 5000)

    def test_generate_planner_supports_device_and_layout_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "planner_palma.pdf"
            generated_path = generate_planner(
                year=2026,
                output_path=output_path,
                device="palma",
                layout="compact",
            )

            self.assertEqual(generated_path, output_path)
            self.assertTrue(output_path.exists())

            data = output_path.read_bytes()
            self.assertTrue(data.startswith(b"%PDF"))
            self.assertEqual(
                len(_PDF_PAGE_PATTERN.findall(data)),
                expected_page_count(2026, device="palma", layout="compact"),
            )

    def test_generate_planner_rejects_unknown_device_or_layout(self) -> None:
        with self.assertRaises(ValueError):
            generate_planner(year=2026, output_path=Path("unused.pdf"), device="unknown")
        with self.assertRaises(ValueError):
            generate_planner(year=2026, output_path=Path("unused.pdf"), layout="unknown")

    def test_generate_planner_strict_layout_rejects_non_fitting_profile(self) -> None:
        with self.assertRaises(ValueError):
            generate_planner(
                year=2026,
                output_path=Path("unused.pdf"),
                device="palma",
                layout="full",
                strict_layout=True,
            )


class PlannerStructureTests(unittest.TestCase):
    def test_expected_page_count_matches_calendar_data(self) -> None:
        computed = 1 + 12
        computed += sum(len(calendar.monthcalendar(2026, month)) for month in range(1, 13))
        computed += sum(calendar.monthrange(2026, month)[1] for month in range(1, 13))
        self.assertEqual(expected_page_count(2026), computed)

    def test_compact_layout_has_additional_week_pages(self) -> None:
        self.assertGreater(
            expected_page_count(2026, device="palma", layout="compact"),
            expected_page_count(2026),
        )

    def test_non_strict_page_count_falls_back_to_fitting_layout(self) -> None:
        self.assertEqual(
            expected_page_count(2026, device="palma", layout="full"),
            expected_page_count(2026, device="palma", layout="compact"),
        )
        with self.assertRaises(ValueError):
            expected_page_count(
                2026,
                device="palma",
                layout="full",
                strict_layout=True,
            )

    def test_bookmark_helpers_validate_input(self) -> None:
        with self.assertRaises(ValueError):
            month_bookmark(0)
        with self.assertRaises(ValueError):
            week_bookmark(1, 0)
        self.assertEqual(day_bookmark(date(2026, 2, 15)), "Day_2026_02_15")
