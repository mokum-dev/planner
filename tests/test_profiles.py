"""Tests for device and layout profile resolution."""

from __future__ import annotations

import unittest

from planner.config import PAGE_HEIGHT, PAGE_WIDTH, SIDEBAR_WIDTH
from planner.profiles import (
    DEFAULT_RENDER_PROFILE,
    evaluate_render_profile_fit,
    resolve_fitted_render_profile,
    resolve_render_profile,
)


class RenderProfileTests(unittest.TestCase):
    def test_default_profile_matches_legacy_geometry(self) -> None:
        self.assertEqual(DEFAULT_RENDER_PROFILE.page_width, PAGE_WIDTH)
        self.assertEqual(DEFAULT_RENDER_PROFILE.page_height, PAGE_HEIGHT)
        self.assertEqual(DEFAULT_RENDER_PROFILE.sidebar_width, SIDEBAR_WIDTH)
        self.assertTrue(DEFAULT_RENDER_PROFILE.layout.show_sidebar)

    def test_device_default_layout_for_palma_is_compact(self) -> None:
        profile = resolve_render_profile(device="palma")
        self.assertEqual(profile.layout.name, "compact")
        self.assertFalse(profile.layout.show_sidebar)
        self.assertTrue(profile.device.compact_day_at_glance)
        self.assertAlmostEqual(profile.device.template_font_scale, 0.75)
        self.assertEqual(profile.layout.week.segments, ((0, 1, 2, 3), (4, 5, 6)))
        self.assertFalse(profile.layout.daily.show_schedule)
        self.assertFalse(profile.layout.daily.show_priorities)

    def test_resolve_profile_rejects_unknown_names(self) -> None:
        with self.assertRaises(ValueError):
            resolve_render_profile(device="not-a-device")
        with self.assertRaises(ValueError):
            resolve_render_profile(layout="not-a-layout")

    def test_fit_evaluation_flags_small_device_full_layout(self) -> None:
        issues = evaluate_render_profile_fit(resolve_render_profile(device="palma", layout="full"))
        self.assertTrue(any("weekly column width" in issue for issue in issues))

    def test_fitted_resolution_falls_back_to_compact(self) -> None:
        resolution = resolve_fitted_render_profile(device="palma", layout="full")
        self.assertTrue(resolution.fallback_applied)
        self.assertEqual(resolution.requested_layout, "full")
        self.assertEqual(resolution.selected_layout, "compact")
        self.assertTrue(resolution.requested_issues)

    def test_fitted_resolution_strict_rejects_non_fitting_layout(self) -> None:
        with self.assertRaises(ValueError):
            resolve_fitted_render_profile(device="palma", layout="full", strict_layout=True)
