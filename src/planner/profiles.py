"""Device and layout profiles for planner rendering."""

from __future__ import annotations

from dataclasses import dataclass

from .config import HEADER_HEIGHT, PAGE_HEIGHT, PAGE_WIDTH, SIDEBAR_WIDTH


@dataclass(frozen=True)
class DeviceProfile:
    """Physical page configuration for a target e-ink device."""

    name: str
    page_width: int
    page_height: int
    pixels_per_inch: int = 226
    template_font_scale: float = 1.0
    compact_day_at_glance: bool = False
    margin: int = 50
    sidebar_width: int = SIDEBAR_WIDTH
    header_height: int = HEADER_HEIGHT
    safe_tap_min: int = 24
    min_month_cell_width: int = 100
    min_week_column_width: int = 100
    min_daily_section_width: int = 220


@dataclass(frozen=True)
class MonthLayoutProfile:
    """Monthly view density and feature toggles."""

    side_padding: int = 40
    top_padding: int = 60
    bottom_padding: int = 150
    show_week_labels: bool = True
    weekday_label_font_size: int = 18
    day_number_font_size: int = 22
    day_number_box_height: int = 34
    day_number_box_max_width: int = 58
    week_label_width: int = 24
    week_label_gap: int = 8
    week_label_font_size: int = 14
    draw_writing_line: bool = True
    writing_line_margin: int = 10


@dataclass(frozen=True)
class WeekLayoutProfile:
    """Weekly view density and segmentation rules."""

    segments: tuple[tuple[int, ...], ...] = ((0, 1, 2, 3, 4, 5, 6),)


@dataclass(frozen=True)
class DailyLayoutProfile:
    """Daily view section toggles and writing-grid density."""

    show_schedule: bool = True
    show_priorities: bool = True
    notes_grid_step_mm: float = 5.0


@dataclass(frozen=True)
class LayoutProfile:
    """Logical layout profile independent of physical page dimensions."""

    name: str
    show_sidebar: bool
    month: MonthLayoutProfile
    week: WeekLayoutProfile
    daily: DailyLayoutProfile


@dataclass(frozen=True)
class RenderProfile:
    """Resolved render profile composed from device + layout."""

    device: DeviceProfile
    layout: LayoutProfile

    @property
    def page_width(self) -> int:
        return self.device.page_width

    @property
    def page_height(self) -> int:
        return self.device.page_height

    @property
    def header_height(self) -> int:
        return self.device.header_height

    @property
    def sidebar_width(self) -> int:
        return self.device.sidebar_width if self.layout.show_sidebar else 0

    @property
    def content_left(self) -> int:
        return self.sidebar_width + self.device.margin


@dataclass(frozen=True)
class ProfileResolution:
    """Profile resolution metadata including fallback details."""

    profile: RenderProfile
    requested_layout: str
    selected_layout: str
    fallback_applied: bool
    requested_issues: tuple[str, ...]


DEVICE_PROFILES = {
    "remarkable": DeviceProfile(
        name="reMarkable 2",
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
        pixels_per_inch=226,
    ),
    "scribe": DeviceProfile(
        name="Kindle Scribe",
        page_width=1860,
        page_height=2480,
        pixels_per_inch=300,
    ),
    "palma": DeviceProfile(
        name="BOOX Palma",
        page_width=824,
        page_height=1648,
        pixels_per_inch=300,
        template_font_scale=0.75,
        compact_day_at_glance=True,
        margin=28,
        safe_tap_min=28,
    ),
}


LAYOUT_DENSITY_ORDER = ("full", "balanced", "compact")

LAYOUT_PROFILES = {
    "full": LayoutProfile(
        name="full",
        show_sidebar=True,
        month=MonthLayoutProfile(),
        week=WeekLayoutProfile(),
        daily=DailyLayoutProfile(),
    ),
    "balanced": LayoutProfile(
        name="balanced",
        show_sidebar=True,
        month=MonthLayoutProfile(
            day_number_font_size=20,
            weekday_label_font_size=16,
            week_label_font_size=12,
        ),
        week=WeekLayoutProfile(),
        daily=DailyLayoutProfile(),
    ),
    "compact": LayoutProfile(
        name="compact",
        show_sidebar=False,
        month=MonthLayoutProfile(
            show_week_labels=False,
            day_number_font_size=18,
            day_number_box_height=30,
            day_number_box_max_width=50,
            weekday_label_font_size=14,
            draw_writing_line=False,
        ),
        week=WeekLayoutProfile(
            segments=((0, 1, 2, 3), (4, 5, 6)),
        ),
        daily=DailyLayoutProfile(
            show_schedule=False,
            show_priorities=False,
            notes_grid_step_mm=6.0,
        ),
    ),
}


DEFAULT_LAYOUT_BY_DEVICE = {
    "remarkable": "full",
    "scribe": "full",
    "palma": "compact",
}

DEFAULT_DEVICE = "remarkable"


def resolve_render_profile(
    device: str = DEFAULT_DEVICE,
    layout: str | None = None,
) -> RenderProfile:
    """Resolve built-in device and layout names into a render profile."""
    if device not in DEVICE_PROFILES:
        msg = f"unknown device '{device}'. Valid devices: {', '.join(sorted(DEVICE_PROFILES))}."
        raise ValueError(msg)

    layout_name = layout or DEFAULT_LAYOUT_BY_DEVICE[device]
    if layout_name not in LAYOUT_PROFILES:
        msg = (
            f"unknown layout '{layout_name}'. Valid layouts: {', '.join(sorted(LAYOUT_PROFILES))}."
        )
        raise ValueError(msg)

    return RenderProfile(device=DEVICE_PROFILES[device], layout=LAYOUT_PROFILES[layout_name])


def _layout_candidates(layout_name: str, *, strict_layout: bool) -> tuple[str, ...]:
    if strict_layout:
        return (layout_name,)
    if layout_name not in LAYOUT_DENSITY_ORDER:
        return (layout_name,)
    start_idx = LAYOUT_DENSITY_ORDER.index(layout_name)
    return LAYOUT_DENSITY_ORDER[start_idx:]


def evaluate_render_profile_fit(profile: RenderProfile) -> tuple[str, ...]:
    """Return fit issues for the profile; empty result means the profile is usable."""
    issues: list[str] = []
    device = profile.device
    month = profile.layout.month

    month_width = profile.page_width - profile.sidebar_width - (2 * month.side_padding)
    month_height = profile.page_height - profile.header_height - month.bottom_padding
    if month_width <= 0 or month_height <= 0:
        issues.append("monthly grid area is non-positive")
    else:
        month_col_width = month_width / 7
        month_row_height = month_height / 6
        if month_col_width < device.min_month_cell_width:
            issues.append(
                f"monthly cell width {month_col_width:.1f} < {device.min_month_cell_width}"
            )
        if month_row_height < device.safe_tap_min:
            issues.append(f"monthly cell height {month_row_height:.1f} < {device.safe_tap_min}")
        day_badge_width = min(month.day_number_box_max_width, month_col_width)
        if day_badge_width < device.safe_tap_min:
            issues.append(f"monthly day badge width {day_badge_width:.1f} < {device.safe_tap_min}")
        if month.day_number_box_height < device.safe_tap_min:
            issues.append(
                f"monthly day badge height {month.day_number_box_height} < {device.safe_tap_min}"
            )

    week_width = profile.page_width - profile.sidebar_width - 80
    week_height = profile.page_height - profile.header_height - 260
    if week_width <= 0 or week_height <= 0:
        issues.append("weekly grid area is non-positive")
    else:
        for segment in profile.layout.week.segments:
            if not segment:
                issues.append("weekly segment cannot be empty")
                continue
            if any(idx < 0 or idx > 6 for idx in segment):
                issues.append("weekly segment indexes must be between 0 and 6")
                continue
            segment_col_width = week_width / len(segment)
            if segment_col_width < device.min_week_column_width:
                issues.append(
                    f"weekly column width {segment_col_width:.1f} < {device.min_week_column_width}"
                )
            day_label_width = segment_col_width - 16
            if day_label_width < device.safe_tap_min:
                issues.append(
                    f"weekly day badge width {day_label_width:.1f} < {device.safe_tap_min}"
                )

    daily_total_width = profile.page_width - profile.sidebar_width - 80
    daily_total_height = (profile.page_height - profile.header_height - 90) - 110
    if daily_total_width <= 0 or daily_total_height <= 0:
        issues.append("daily view area is non-positive")
    elif profile.layout.daily.show_schedule:
        schedule_width = daily_total_width / 3
        right_width = daily_total_width - schedule_width - 16
        if schedule_width < device.min_daily_section_width:
            issues.append(
                f"daily schedule section width {schedule_width:.1f} "
                f"< {device.min_daily_section_width}"
            )
        if right_width < device.min_daily_section_width:
            issues.append(
                f"daily notes section width {right_width:.1f} < {device.min_daily_section_width}"
            )
        writable_schedule_width = schedule_width - 42
        if writable_schedule_width < device.safe_tap_min:
            issues.append(
                f"daily schedule writable width {writable_schedule_width:.1f} "
                f"< {device.safe_tap_min}"
            )
    elif (
        profile.layout.daily.show_priorities and daily_total_width < device.min_daily_section_width
    ):
        issues.append(
            f"daily priorities section width {daily_total_width:.1f} "
            f"< {device.min_daily_section_width}"
        )

    if profile.layout.daily.notes_grid_step_mm <= 0:
        issues.append("daily notes grid step must be positive")

    return tuple(issues)


def resolve_fitted_render_profile(
    device: str = DEFAULT_DEVICE,
    layout: str | None = None,
    *,
    strict_layout: bool = False,
) -> ProfileResolution:
    """Resolve a profile and optionally fallback to denser layouts when fit checks fail."""
    if device not in DEVICE_PROFILES:
        msg = f"unknown device '{device}'. Valid devices: {', '.join(sorted(DEVICE_PROFILES))}."
        raise ValueError(msg)

    requested_layout = layout or DEFAULT_LAYOUT_BY_DEVICE[device]
    if requested_layout not in LAYOUT_PROFILES:
        msg = (
            f"unknown layout '{requested_layout}'. Valid layouts: "
            f"{', '.join(sorted(LAYOUT_PROFILES))}."
        )
        raise ValueError(msg)

    candidates = _layout_candidates(requested_layout, strict_layout=strict_layout)
    issues_by_layout: dict[str, tuple[str, ...]] = {}

    for candidate_layout in candidates:
        profile = resolve_render_profile(device=device, layout=candidate_layout)
        fit_issues = evaluate_render_profile_fit(profile)
        if not fit_issues:
            return ProfileResolution(
                profile=profile,
                requested_layout=requested_layout,
                selected_layout=candidate_layout,
                fallback_applied=(candidate_layout != requested_layout),
                requested_issues=issues_by_layout.get(requested_layout, ()),
            )
        issues_by_layout[candidate_layout] = fit_issues

    requested_issues = issues_by_layout.get(requested_layout, ())
    issue_text = "; ".join(requested_issues) if requested_issues else "no detailed issues"
    if strict_layout:
        msg = f"layout '{requested_layout}' does not fit device '{device}': {issue_text}"
    else:
        tried = ", ".join(candidates)
        msg = f"no fitting layout for device '{device}' (tried: {tried}). Issues: {issue_text}"
    raise ValueError(msg)


DEFAULT_RENDER_PROFILE = resolve_fitted_render_profile().profile
