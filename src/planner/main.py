"""CLI and orchestration for planner/template PDF generation."""

from __future__ import annotations

import argparse
import calendar
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .components import (
    draw_breadcrumbs,
    draw_daily_view,
    draw_grid,
    draw_header,
    draw_link_row,
    draw_sidebar,
    draw_week_grid,
)
from .config import DEFAULT_FILENAME_TEMPLATE, Theme
from .drawing import DrawingPrimitives, create_reportlab_primitives
from .profiles import (
    DEFAULT_DEVICE,
    DEVICE_PROFILES,
    LAYOUT_PROFILES,
    RenderProfile,
    resolve_fitted_render_profile,
)
from .rendering import render_page_block
from .template_blocks import CallbackBlock
from .template_engine import Rect, RenderContext, parse_param_pairs
from .theme_profiles import available_theme_profiles, resolve_theme
from .templates import (
    TEMPLATE_LAYOUT_PROFILES,
    generate_template,
    get_template_spec,
    list_template_specs,
)

WEEKDAY_LABELS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


@dataclass(frozen=True)
class WeekSegmentPlan:
    """One weekly page segment with its own destination bookmark."""

    bookmark: str
    day_indexes: tuple[int, ...]
    label: str


@dataclass(frozen=True)
class WeekPlan:
    """A month week plus one or more render segments."""

    week_idx: int
    iso_week: int
    segments: tuple[WeekSegmentPlan, ...]


def _validate_year(year: int) -> None:
    if isinstance(year, bool) or not isinstance(year, int):
        msg = "year must be an integer."
        raise TypeError(msg)
    if year < 1:
        msg = "year must be >= 1."
        raise ValueError(msg)


def month_matrix(year: int, month: int) -> list[list[int]]:
    """Return the month grid in Monday-first format."""
    _validate_year(year)
    if not 1 <= month <= 12:
        msg = "month must be between 1 and 12."
        raise ValueError(msg)
    return calendar.monthcalendar(year, month)


def month_bookmark(month: int) -> str:
    """Return a bookmark id for a month overview page."""
    if not 1 <= month <= 12:
        msg = "month must be between 1 and 12."
        raise ValueError(msg)
    return f"Month_{month}"


def week_bookmark(month: int, week_idx: int) -> str:
    """Return a bookmark id for a month-specific week page."""
    if not 1 <= month <= 12:
        msg = "month must be between 1 and 12."
        raise ValueError(msg)
    if week_idx < 1:
        msg = "week_idx must be >= 1."
        raise ValueError(msg)
    return f"Week_{month}_{week_idx}"


def day_bookmark(page_date: date) -> str:
    """Return a bookmark id for a single daily page."""
    return f"Day_{page_date.year}_{page_date.month:02d}_{page_date.day:02d}"


def _week_part_bookmark(month: int, week_idx: int, part_idx: int) -> str:
    """Return a bookmark id for additional week segments."""
    if part_idx < 1:
        msg = "part_idx must be >= 1."
        raise ValueError(msg)
    base = week_bookmark(month, week_idx)
    if part_idx == 1:
        return base
    return f"{base}_P{part_idx}"


def _segment_label(day_indexes: Sequence[int]) -> str:
    if not day_indexes:
        msg = "day_indexes cannot be empty."
        raise ValueError(msg)
    first = WEEKDAY_LABELS[day_indexes[0]]
    last = WEEKDAY_LABELS[day_indexes[-1]]
    if first == last:
        return first
    return f"{first}-{last}"


def _week_segments_for_week(
    week: Sequence[int],
    profile: RenderProfile,
) -> tuple[tuple[int, ...], ...]:
    """Return non-empty week segments for the active layout profile."""
    segments: list[tuple[int, ...]] = []
    for segment in profile.layout.week.segments:
        if not segment:
            continue
        if any(idx < 0 or idx > 6 for idx in segment):
            msg = "week segment indexes must be between 0 and 6."
            raise ValueError(msg)
        if any(week[idx] for idx in segment):
            segments.append(segment)
    if segments:
        return tuple(segments)
    return (tuple(range(7)),)


def expected_page_count(
    year: int,
    *,
    device: str = DEFAULT_DEVICE,
    layout: str | None = None,
    strict_layout: bool = False,
) -> int:
    """Return expected total page count for cover + month + week + day views."""
    _validate_year(year)
    profile = resolve_fitted_render_profile(
        device=device,
        layout=layout,
        strict_layout=strict_layout,
    ).profile
    week_pages = 0
    for month in range(1, 13):
        matrix = month_matrix(year, month)
        week_pages += sum(len(_week_segments_for_week(week, profile)) for week in matrix)
    day_pages = sum(calendar.monthrange(year, month)[1] for month in range(1, 13))
    return 1 + 12 + week_pages + day_pages


def _render_planner_page(
    pdf: DrawingPrimitives,
    *,
    profile: RenderProfile,
    theme: type,
    draw_page: Callable[[DrawingPrimitives], None],
) -> None:
    def render_with_context(ctx: RenderContext, rect: Rect) -> None:
        _ = rect
        draw_page(ctx.pdf)

    render_page_block(
        pdf,
        block=CallbackBlock(callback=render_with_context),
        device_profile=profile.device,
        layout_profile=profile.layout,
        theme=theme,
    )


def generate_planner(
    year: int = 2026,
    output_path: str | Path | None = None,
    *,
    device: str = DEFAULT_DEVICE,
    layout: str | None = None,
    strict_layout: bool = False,
    theme: type = Theme,
) -> Path:
    """Generate a planner PDF and return the output path."""
    _validate_year(year)
    profile = resolve_fitted_render_profile(
        device=device,
        layout=layout,
        strict_layout=strict_layout,
    ).profile

    destination = Path(output_path or DEFAULT_FILENAME_TEMPLATE.format(year=year))
    destination.parent.mkdir(parents=True, exist_ok=True)

    pdf = create_reportlab_primitives(
        str(destination),
        pagesize=(profile.page_width, profile.page_height),
    )
    pdf.set_title(f"Planner {year} ({profile.device.name}, {profile.layout.name})")

    month_matrices: dict[int, list[list[int]]] = {}
    day_to_week_maps: dict[int, dict[int, int]] = {}
    week_number_maps: dict[int, dict[int, int]] = {}
    week_plans_by_month: dict[int, list[WeekPlan]] = {}
    month_week_destinations: dict[int, dict[int, str]] = {}
    day_to_week_bookmarks: dict[date, str] = {}
    all_dates: list[date] = []
    for month in range(1, 13):
        matrix = month_matrix(year, month)
        day_to_week: dict[int, int] = {}
        week_numbers: dict[int, int] = {}
        week_plans: list[WeekPlan] = []
        for week_idx, week in enumerate(matrix, start=1):
            first_day_in_week = next((day_num for day_num in week if day_num), None)
            if first_day_in_week is not None:
                week_numbers[week_idx] = date(year, month, first_day_in_week).isocalendar().week
            else:
                msg = "calendar week must include at least one day."
                raise ValueError(msg)

            week_segments = _week_segments_for_week(week, profile)
            segment_plans: list[WeekSegmentPlan] = []
            for segment_idx, day_indexes in enumerate(week_segments, start=1):
                segment_bookmark = _week_part_bookmark(month, week_idx, segment_idx)
                segment_plans.append(
                    WeekSegmentPlan(
                        bookmark=segment_bookmark,
                        day_indexes=day_indexes,
                        label=_segment_label(day_indexes),
                    )
                )
                for day_offset in day_indexes:
                    day_num = week[day_offset]
                    if day_num:
                        day_to_week_bookmarks[date(year, month, day_num)] = segment_bookmark

            week_plans.append(
                WeekPlan(
                    week_idx=week_idx,
                    iso_week=week_numbers[week_idx],
                    segments=tuple(segment_plans),
                )
            )
            for day_num in week:
                if day_num:
                    day_to_week[day_num] = week_idx
                    all_dates.append(date(year, month, day_num))
        month_matrices[month] = matrix
        day_to_week_maps[month] = day_to_week
        week_number_maps[month] = week_numbers
        week_plans_by_month[month] = week_plans
        month_week_destinations[month] = {
            week_plan.week_idx: week_plan.segments[0].bookmark for week_plan in week_plans
        }

    def draw_cover_page(page_pdf: DrawingPrimitives) -> None:
        draw_sidebar(page_pdf, active_month_idx=0, profile=profile, theme=theme)
        page_pdf.set_fill_color(theme.TEXT_PRIMARY)
        page_pdf.set_font(theme.FONT_HEADER, 100)
        sidebar_offset = profile.sidebar_width if profile.layout.show_sidebar else 0
        cover_center_x = (profile.page_width + sidebar_offset) / 2
        page_pdf.draw_centred_string(cover_center_x, profile.page_height / 2, str(year))

        draw_link_row(
            page_pdf,
            [
                ("MONTH VIEW", month_bookmark(1)),
                ("WEEK VIEW", week_bookmark(1, 1)),
                ("DAY VIEW", day_bookmark(all_dates[0])),
            ],
            y=(profile.page_height / 2) - 80,
            profile=profile,
            theme=theme,
        )
        page_pdf.bookmark_page("Cover")

    _render_planner_page(pdf, profile=profile, theme=theme, draw_page=draw_cover_page)

    for month in range(1, 13):
        def draw_month_page(page_pdf: DrawingPrimitives, *, current_month: int = month) -> None:
            current_month_name = calendar.month_name[current_month]
            current_bookmark = month_bookmark(current_month)
            current_matrix = month_matrices[current_month]

            page_pdf.bookmark_page(current_bookmark)
            page_pdf.add_outline_entry(f"{current_month_name} (Monthly)", current_bookmark, level=0)

            draw_sidebar(page_pdf, active_month_idx=current_month, profile=profile, theme=theme)
            draw_header(
                page_pdf,
                title=current_month_name.upper(),
                subtitle=str(year),
                profile=profile,
                theme=theme,
            )
            draw_breadcrumbs(
                page_pdf,
                [("COVER", "Cover"), (current_month_name.upper(), None)],
                profile=profile,
                theme=theme,
            )
            draw_grid(
                page_pdf,
                calendar_matrix=current_matrix,
                day_destinations={
                    day_num: day_bookmark(date(year, current_month, day_num))
                    for day_num in range(1, calendar.monthrange(year, current_month)[1] + 1)
                },
                week_destinations=month_week_destinations[current_month],
                week_labels={
                    week_idx: f"W{week_number_maps[current_month][week_idx]:02d}"
                    for week_idx in range(1, len(current_matrix) + 1)
                },
                profile=profile,
                theme=theme,
            )

        _render_planner_page(pdf, profile=profile, theme=theme, draw_page=draw_month_page)

    for month in range(1, 13):
        month_name = calendar.month_name[month]
        matrix = month_matrices[month]
        week_plans = week_plans_by_month[month]

        day_destinations = {
            day_num: day_bookmark(date(year, month, day_num))
            for day_num in range(1, calendar.monthrange(year, month)[1] + 1)
        }

        for week, week_plan in zip(matrix, week_plans, strict=True):
            segments = week_plan.segments
            for segment_idx, segment in enumerate(segments):
                def draw_week_page(
                    page_pdf: DrawingPrimitives,
                    *,
                    current_month: int = month,
                    current_month_name: str = month_name,
                    current_week: list[int] = week,
                    current_week_plan: WeekPlan = week_plan,
                    current_segments: tuple[WeekSegmentPlan, ...] = segments,
                    current_segment_idx: int = segment_idx,
                    current_segment: WeekSegmentPlan = segment,
                ) -> None:
                    bookmark = current_segment.bookmark
                    page_pdf.bookmark_page(bookmark)

                    if current_segment_idx == 0:
                        outline_title = f"Week {current_week_plan.iso_week:02d}"
                    else:
                        outline_title = f"Week {current_week_plan.iso_week:02d} ({current_segment.label})"
                    page_pdf.add_outline_entry(outline_title, bookmark, level=1)

                    draw_sidebar(page_pdf, active_month_idx=current_month, profile=profile, theme=theme)
                    subtitle_suffix = f"{current_segment.label} | " if len(current_segments) > 1 else ""
                    draw_header(
                        page_pdf,
                        title=current_month_name.upper(),
                        subtitle=f"WEEK {current_week_plan.iso_week:02d} | {subtitle_suffix}{year}",
                        title_size=62,
                        subtitle_size=34,
                        profile=profile,
                        theme=theme,
                    )
                    crumb_label = f"W{current_week_plan.iso_week:02d}"
                    if len(current_segments) > 1:
                        crumb_label = f"{crumb_label} {current_segment.label}"
                    draw_breadcrumbs(
                        page_pdf,
                        [
                            ("COVER", "Cover"),
                            (current_month_name.upper(), month_bookmark(current_month)),
                            (crumb_label, None),
                        ],
                        profile=profile,
                        theme=theme,
                    )

                    week_links: list[tuple[str, str]] = []
                    if current_segment_idx > 0:
                        week_links.append(("PREV PART", current_segments[current_segment_idx - 1].bookmark))
                    elif current_week_plan.week_idx > 1:
                        prev_week_segments = week_plans[current_week_plan.week_idx - 2].segments
                        week_links.append(("PREV WEEK", prev_week_segments[-1].bookmark))

                    if current_segment_idx < len(current_segments) - 1:
                        week_links.append(("NEXT PART", current_segments[current_segment_idx + 1].bookmark))
                    elif current_week_plan.week_idx < len(week_plans):
                        next_week_segments = week_plans[current_week_plan.week_idx].segments
                        week_links.append(("NEXT WEEK", next_week_segments[0].bookmark))

                    first_day_in_segment = next(
                        (current_week[idx] for idx in current_segment.day_indexes if current_week[idx]),
                        None,
                    )
                    if first_day_in_segment is not None:
                        week_links.append(
                            ("FIRST DAY", day_bookmark(date(year, current_month, first_day_in_segment)))
                        )

                    draw_link_row(
                        page_pdf,
                        week_links,
                        y=profile.page_height - 215,
                        align="right",
                        profile=profile,
                        theme=theme,
                    )
                    draw_week_grid(
                        page_pdf,
                        week=current_week,
                        day_destinations=day_destinations,
                        day_indexes=current_segment.day_indexes,
                        profile=profile,
                        theme=theme,
                    )

                _render_planner_page(pdf, profile=profile, theme=theme, draw_page=draw_week_page)

    for day_idx, page_date in enumerate(all_dates):
        month_name = calendar.month_name[page_date.month]
        weekday_name = calendar.day_name[page_date.weekday()]
        bookmark = day_bookmark(page_date)
        week_idx = day_to_week_maps[page_date.month][page_date.day]
        iso_week = week_number_maps[page_date.month][week_idx]

        def draw_day_page(
            page_pdf: DrawingPrimitives,
            *,
            current_day_idx: int = day_idx,
            current_page_date: date = page_date,
            current_month_name: str = month_name,
            current_weekday_name: str = weekday_name,
            current_bookmark: str = bookmark,
            current_iso_week: int = iso_week,
        ) -> None:
            page_pdf.bookmark_page(current_bookmark)

            draw_sidebar(page_pdf, active_month_idx=current_page_date.month, profile=profile, theme=theme)
            draw_header(
                page_pdf,
                title=current_weekday_name.upper(),
                subtitle=f"{current_month_name} {current_page_date.day}, {year}",
                title_size=56,
                subtitle_size=32,
                profile=profile,
                theme=theme,
            )
            draw_breadcrumbs(
                page_pdf,
                [
                    ("COVER", "Cover"),
                    (current_month_name.upper(), month_bookmark(current_page_date.month)),
                    (f"W{current_iso_week:02d}", day_to_week_bookmarks[current_page_date]),
                    (f"DAY {current_page_date.day:02d}", None),
                ],
                profile=profile,
                theme=theme,
            )

            day_links: list[tuple[str, str]] = []
            if current_day_idx > 0:
                day_links.append(("PREV DAY", day_bookmark(all_dates[current_day_idx - 1])))
            if current_day_idx < len(all_dates) - 1:
                day_links.append(("NEXT DAY", day_bookmark(all_dates[current_day_idx + 1])))

            draw_link_row(
                page_pdf,
                day_links,
                y=profile.page_height - 215,
                align="right",
                profile=profile,
                theme=theme,
            )
            draw_daily_view(page_pdf, page_date=current_page_date, profile=profile, theme=theme)

        _render_planner_page(pdf, profile=profile, theme=theme, draw_page=draw_day_page)

    pdf.save()
    return destination


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate planner and note-template PDFs.")
    parser.add_argument("--year", type=int, default=2026, help="Year to render.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output PDF path. Default: planner_<year>.pdf",
    )
    parser.add_argument(
        "--device",
        choices=sorted(DEVICE_PROFILES),
        default=DEFAULT_DEVICE,
        help="Target device profile.",
    )
    parser.add_argument(
        "--layout",
        choices=sorted(LAYOUT_PROFILES),
        default=None,
        help="Layout profile. Default is device-specific with auto-fit fallback.",
    )
    parser.add_argument(
        "--strict-layout",
        action="store_true",
        help="Disable auto-fit fallback and require the requested layout to fit.",
    )
    parser.add_argument(
        "--theme-profile",
        choices=available_theme_profiles(),
        default="default",
        help="Built-in theme profile name.",
    )
    parser.add_argument(
        "--theme-file",
        type=Path,
        default=None,
        help="JSON file with theme overrides.",
    )
    return parser


def _build_templates_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect available template specs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available templates.")
    list_parser.add_argument(
        "--template-plugin",
        action="append",
        default=[],
        help="Additional template plugin module path (repeatable).",
    )

    show_parser = subparsers.add_parser("show", help="Show details for one template.")
    show_parser.add_argument("template", help="Template id or alias.")
    show_parser.add_argument(
        "--template-plugin",
        action="append",
        default=[],
        help="Additional template plugin module path (repeatable).",
    )

    generate_parser = subparsers.add_parser("generate", help="Generate one template PDF.")
    generate_parser.add_argument("template", help="Template id or alias.")
    generate_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output PDF path. Default: template_<template>_<device>.pdf",
    )
    generate_parser.add_argument(
        "--device",
        choices=sorted(DEVICE_PROFILES),
        default=DEFAULT_DEVICE,
        help="Target device profile.",
    )
    generate_parser.add_argument(
        "--layout",
        choices=sorted(TEMPLATE_LAYOUT_PROFILES),
        default=None,
        help="Template layout profile (full/balanced/compact).",
    )
    generate_parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Template parameter override in key=value form (repeatable).",
    )
    generate_parser.add_argument(
        "--template-plugin",
        action="append",
        default=[],
        help="Additional template plugin module path (repeatable).",
    )
    generate_parser.add_argument(
        "--theme-profile",
        choices=available_theme_profiles(),
        default="default",
        help="Built-in theme profile name.",
    )
    generate_parser.add_argument(
        "--theme-file",
        type=Path,
        default=None,
        help="JSON file with theme overrides.",
    )
    return parser


def _run_templates_cli(argv: list[str]) -> int:
    parser = _build_templates_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            for spec in list_template_specs(plugin_modules=args.template_plugin):
                print(f"{spec.template_id}\t{spec.title}")
            return 0

        if args.command == "show":
            spec = get_template_spec(args.template, plugin_modules=args.template_plugin)
            print(f"id: {spec.template_id}")
            print(f"title: {spec.title}")
            print(f"description: {spec.description}")
            if spec.aliases:
                print(f"aliases: {', '.join(spec.aliases)}")
            if spec.supported_devices:
                print(f"devices: {', '.join(spec.supported_devices)}")
            print("params:")
            if not spec.params:
                print("  (none)")
                return 0
            for param in spec.params:
                suffix_parts: list[str] = []
                if param.choices:
                    suffix_parts.append(f"choices={','.join(str(choice) for choice in param.choices)}")
                if param.min_value is not None:
                    suffix_parts.append(f"min={param.min_value}")
                if param.max_value is not None:
                    suffix_parts.append(f"max={param.max_value}")
                if param.has_default:
                    suffix_parts.append(f"default={param.default}")
                suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ""
                print(f"  {param.key}: {param.description}{suffix}")
            return 0

        if args.command == "generate":
            raw_template_params = parse_param_pairs(args.param)
            resolved_theme = resolve_theme(profile=args.theme_profile, theme_file=args.theme_file)
            destination = generate_template(
                template=args.template,
                output_path=args.output,
                device=args.device,
                layout=args.layout,
                param_overrides=raw_template_params,
                plugin_modules=args.template_plugin,
                theme=resolved_theme,
            )
            print(f"Generated template at: {destination}")
            return 0
    except ValueError as exc:
        parser.exit(status=2, message=f"error: {exc}\n")

    parser.exit(status=2, message=f"error: unknown templates command '{args.command}'\n")
    return 2


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    if argv_list and argv_list[0] == "templates":
        return _run_templates_cli(argv_list[1:])

    parser = _build_arg_parser()
    args = parser.parse_args(argv_list)

    try:
        resolved_theme = resolve_theme(profile=args.theme_profile, theme_file=args.theme_file)
        destination = generate_planner(
            year=args.year,
            output_path=args.output,
            device=args.device,
            layout=args.layout,
            strict_layout=args.strict_layout,
            theme=resolved_theme,
        )
    except ValueError as exc:
        parser.exit(status=2, message=f"error: {exc}\n")

    print(f"Generated planner at: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
