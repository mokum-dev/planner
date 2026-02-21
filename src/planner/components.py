"""Rendering helpers for planner PDF pages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from .config import MONTH_LABELS, Theme
from .drawing import DrawingPrimitives
from .planner_geometry import (
    ascending_step_positions,
    compute_daily_view_geometry,
    compute_month_grid_geometry,
    compute_week_grid_geometry,
    daily_priorities_row_bounds,
    daily_schedule_row_bounds,
    month_cell_rect,
    month_day_badge_rect,
    month_week_label_rect,
    month_weekday_label_center,
    month_writing_line_points,
    week_column_rect,
    week_day_label_rect,
    week_writing_line_y_positions,
)
from .profiles import DEFAULT_RENDER_PROFILE, RenderProfile

WEEKDAY_LABELS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def draw_sidebar(
    pdf: DrawingPrimitives,
    active_month_idx: int,
    *,
    profile: RenderProfile = DEFAULT_RENDER_PROFILE,
    theme: type = Theme,
) -> None:
    """Draw the left navigation sidebar and month links.

    `active_month_idx` may be 0 (no active month) or 1-12.
    """
    if not 0 <= active_month_idx <= 12:
        msg = "active_month_idx must be between 0 and 12."
        raise ValueError(msg)
    if not profile.layout.show_sidebar:
        return

    sidebar_width = profile.sidebar_width
    page_height = profile.page_height

    pdf.set_fill_color(theme.SIDEBAR_BG)
    pdf.rect(0, 0, sidebar_width, page_height, fill=1, stroke=0)

    button_height = page_height / len(MONTH_LABELS)

    for index, month_abbr in enumerate(MONTH_LABELS, start=1):
        y_pos = page_height - (index * button_height)

        if index == active_month_idx:
            pdf.set_fill_color(theme.ACCENT)
            pdf.rect(0, y_pos, sidebar_width, button_height, fill=1, stroke=0)

        font_size = min(24, max(10, int(button_height * 0.16)))
        pdf.set_fill_color(theme.SIDEBAR_TEXT)
        pdf.set_font(theme.FONT_BOLD, font_size)
        text_width = pdf.string_width(month_abbr, theme.FONT_BOLD, font_size)

        text_x = (sidebar_width - text_width) / 2
        text_y = y_pos + (button_height / 2) - (font_size / 3)
        pdf.draw_string(text_x, text_y, month_abbr)

        rect = (0, y_pos, sidebar_width, y_pos + button_height)
        pdf.link_rect(f"Month_{index}", rect)


def draw_header(
    pdf: DrawingPrimitives,
    title: str,
    subtitle: str,
    *,
    title_size: int = 80,
    subtitle_size: int = 40,
    profile: RenderProfile = DEFAULT_RENDER_PROFILE,
    theme: type = Theme,
) -> None:
    """Draw the top header area."""
    pdf.set_fill_color(theme.TEXT_PRIMARY)
    pdf.set_font(theme.FONT_HEADER, title_size)
    pdf.draw_string(profile.content_left, profile.page_height - 120, title)

    pdf.set_fill_color(theme.ACCENT)
    pdf.set_font(theme.FONT_HEADER, subtitle_size)
    pdf.draw_string(profile.content_left, profile.page_height - 170, subtitle)


def draw_breadcrumbs(
    pdf: DrawingPrimitives,
    crumbs: Sequence[tuple[str, str | None]],
    *,
    profile: RenderProfile = DEFAULT_RENDER_PROFILE,
    theme: type = Theme,
) -> None:
    """Draw linked breadcrumb items near the top of the page."""
    if not crumbs:
        msg = "crumbs cannot be empty."
        raise ValueError(msg)

    x_pos = profile.content_left
    y_pos = profile.page_height - 45
    label_size = 15

    for index, (label, destination) in enumerate(crumbs):
        pdf.set_font(theme.FONT_BOLD, label_size)
        pdf.set_fill_color(theme.ACCENT if destination else theme.TEXT_PRIMARY)
        pdf.draw_string(x_pos, y_pos, label)
        label_width = pdf.string_width(label, theme.FONT_BOLD, label_size)

        if destination:
            rect = (x_pos - 2, y_pos - 2, x_pos + label_width + 2, y_pos + 18)
            pdf.link_rect(destination, rect)

        x_pos += label_width
        if index < len(crumbs) - 1:
            separator = " > "
            pdf.set_font(theme.FONT_REGULAR, label_size)
            pdf.set_fill_color(theme.TEXT_SECONDARY)
            pdf.draw_string(x_pos, y_pos, separator)
            x_pos += pdf.string_width(separator, theme.FONT_REGULAR, label_size)


def draw_link_row(
    pdf: DrawingPrimitives,
    links: Sequence[tuple[str, str]],
    *,
    y: float,
    align: str = "left",
    profile: RenderProfile = DEFAULT_RENDER_PROFILE,
    theme: type = Theme,
) -> None:
    """Draw linked navigation badges."""
    if align not in {"left", "right"}:
        msg = "align must be either 'left' or 'right'."
        raise ValueError(msg)
    if not links:
        return

    font_size = 14
    padding = 10
    gap = 12
    widths = [
        (pdf.string_width(label, theme.FONT_BOLD, font_size) + (2 * padding)) for label, _ in links
    ]
    total_width = sum(widths) + (gap * (len(widths) - 1))

    if align == "left":
        x_pos = profile.content_left
    else:
        right_padding = max(12, profile.device.margin - 10)
        x_pos = profile.page_width - right_padding - total_width

    for (label, destination), width in zip(links, widths, strict=True):
        pdf.set_stroke_color(theme.ACCENT)
        pdf.set_line_width(1.2)
        pdf.round_rect(x_pos, y - 3, width, 22, 4, fill=0, stroke=1)

        pdf.set_font(theme.FONT_BOLD, font_size)
        pdf.set_fill_color(theme.ACCENT)
        pdf.draw_centred_string(x_pos + (width / 2), y + 3, label)

        rect = (x_pos, y - 3, x_pos + width, y + 19)
        pdf.link_rect(destination, rect)
        x_pos += width + gap


def draw_grid(
    pdf: DrawingPrimitives,
    calendar_matrix: Sequence[Sequence[int]],
    *,
    day_destinations: Mapping[int, str] | None = None,
    week_destinations: Mapping[int, str] | None = None,
    week_labels: Mapping[int, str] | None = None,
    profile: RenderProfile = DEFAULT_RENDER_PROFILE,
    theme: type = Theme,
) -> None:
    """Draw the planner month grid."""
    if len(calendar_matrix) > 6:
        msg = "calendar_matrix cannot contain more than six weeks."
        raise ValueError(msg)
    if any(len(week) != 7 for week in calendar_matrix):
        msg = "each week in calendar_matrix must have seven days."
        raise ValueError(msg)

    month_profile = profile.layout.month
    geometry = compute_month_grid_geometry(profile)

    pdf.set_font(theme.FONT_BOLD, month_profile.weekday_label_font_size)
    for col_idx, weekday in enumerate(WEEKDAY_LABELS):
        center = month_weekday_label_center(geometry, col_idx)
        pdf.set_fill_color(theme.ACCENT if col_idx >= 5 else theme.TEXT_SECONDARY)
        pdf.draw_centred_string(center.x, center.y, weekday)

    pdf.set_line_width(1)
    pdf.set_stroke_color(theme.GRID_LINES)

    for row_idx in range(6):
        if row_idx < len(calendar_matrix) and week_destinations and month_profile.show_week_labels:
            week_destination = week_destinations.get(row_idx + 1)
            if week_destination:
                week_label = (
                    week_labels.get(row_idx + 1, f"W{row_idx + 1}")
                    if week_labels
                    else f"W{row_idx + 1}"
                )
                header_rect = month_week_label_rect(
                    geometry,
                    row_idx,
                    label_width=month_profile.week_label_width,
                    label_gap=month_profile.week_label_gap,
                )

                pdf.set_stroke_color(theme.GRID_LINES)
                pdf.set_line_width(0.8)
                pdf.rect(
                    header_rect.x,
                    header_rect.y,
                    header_rect.width,
                    header_rect.height,
                    fill=0,
                    stroke=1,
                )

                center_x = header_rect.x + (header_rect.width / 2)
                center_y = header_rect.y + (header_rect.height / 2)
                pdf.save_state()
                pdf.translate(center_x, center_y)
                pdf.rotate(90)
                pdf.set_font(theme.FONT_BOLD, month_profile.week_label_font_size)
                pdf.set_fill_color(theme.ACCENT)
                pdf.draw_centred_string(0, -5, week_label)
                pdf.restore_state()

                rect = (
                    header_rect.x,
                    header_rect.y,
                    header_rect.right,
                    header_rect.top,
                )
                pdf.link_rect(week_destination, rect)

        week = calendar_matrix[row_idx] if row_idx < len(calendar_matrix) else (0,) * 7
        for col_idx, day_num in enumerate(week):
            cell = month_cell_rect(geometry, row_idx, col_idx)

            pdf.set_stroke_color(theme.GRID_LINES)
            pdf.rect(cell.x, cell.y, cell.width, cell.height, fill=0, stroke=1)

            if day_num:
                day_destination = day_destinations.get(day_num) if day_destinations else None
                day_text = str(day_num)
                badge = month_day_badge_rect(
                    cell,
                    box_height=month_profile.day_number_box_height,
                    box_max_width=month_profile.day_number_box_max_width,
                )

                pdf.set_fill_color(theme.LINK_BADGE_BG)
                pdf.set_stroke_color(theme.GRID_LINES)
                pdf.set_line_width(0.8)
                pdf.rect(badge.x, badge.y, badge.width, badge.height, fill=1, stroke=1)

                pdf.set_fill_color(theme.TEXT_PRIMARY)
                pdf.set_font(theme.FONT_BOLD, month_profile.day_number_font_size)
                pdf.draw_centred_string(badge.x + (badge.width / 2), badge.y + 10, day_text)

                if month_profile.draw_writing_line:
                    line_start, line_end = month_writing_line_points(
                        cell,
                        margin=month_profile.writing_line_margin,
                    )
                    pdf.set_stroke_color(theme.WRITING_LINES)
                    pdf.line(line_start.x, line_start.y, line_end.x, line_end.y)

                if day_destination:
                    rect = (badge.x, badge.y, badge.right, badge.top)
                    pdf.link_rect(day_destination, rect)


def draw_week_grid(
    pdf: DrawingPrimitives,
    week: Sequence[int],
    *,
    day_destinations: Mapping[int, str] | None = None,
    day_indexes: Sequence[int] | None = None,
    profile: RenderProfile = DEFAULT_RENDER_PROFILE,
    theme: type = Theme,
) -> None:
    """Draw one-week layout with seven day columns."""
    if len(week) != 7:
        msg = "week must contain exactly seven day entries."
        raise ValueError(msg)
    indexes = tuple(range(7)) if day_indexes is None else tuple(day_indexes)
    if not indexes:
        msg = "day_indexes cannot be empty."
        raise ValueError(msg)
    if any(idx < 0 or idx > 6 for idx in indexes):
        msg = "day_indexes values must be between 0 and 6."
        raise ValueError(msg)

    geometry = compute_week_grid_geometry(profile, column_count=len(indexes))

    for col_idx, weekday_idx in enumerate(indexes):
        day_num = week[weekday_idx]
        column = week_column_rect(geometry, col_idx)

        pdf.set_stroke_color(theme.GRID_LINES)
        pdf.set_line_width(1)
        pdf.rect(column.x, column.y, column.width, column.height, fill=0, stroke=1)

        if not day_num:
            pdf.set_fill_color(theme.TEXT_SECONDARY)
            pdf.set_font(theme.FONT_REGULAR, 18)
            pdf.draw_centred_string(
                column.x + (column.width / 2), column.y + (column.height / 2), "-"
            )
            continue

        label = week_day_label_rect(geometry, column=column)
        label_top = geometry.start_y - geometry.label_top_offset

        day_destination = day_destinations.get(day_num) if day_destinations else None
        if day_destination:
            # Keep tappable area compact for e-ink devices and hint interactivity.
            pdf.set_stroke_color(theme.GRID_LINES)
            pdf.set_line_width(0.8)
            pdf.round_rect(label.x, label.y, label.width, label.height, 5, fill=0, stroke=1)

        label_center_x = label.x + (label.width / 2)
        pdf.set_fill_color(theme.ACCENT if weekday_idx >= 5 else theme.TEXT_SECONDARY)
        pdf.set_font(theme.FONT_BOLD, 13)
        pdf.draw_centred_string(label_center_x, label_top - 18, WEEKDAY_LABELS[weekday_idx])

        pdf.set_fill_color(theme.TEXT_PRIMARY)
        pdf.set_font(theme.FONT_BOLD, 22)
        pdf.draw_centred_string(label_center_x, label_top - 43, f"{day_num:02d}")

        pdf.set_stroke_color(theme.WRITING_LINES)
        for line_y in week_writing_line_y_positions(geometry, column=column):
            pdf.line(
                column.x + geometry.writing_line_horizontal_margin,
                line_y,
                column.right - geometry.writing_line_horizontal_margin,
                line_y,
            )

        if day_destination:
            rect = (label.x, label.y, label.right, label.top)
            pdf.link_rect(day_destination, rect)


def draw_daily_view(
    pdf: DrawingPrimitives,
    page_date: date,
    *,
    profile: RenderProfile = DEFAULT_RENDER_PROFILE,
    theme: type = Theme,
) -> None:
    """Draw the daily planner body."""
    geometry = compute_daily_view_geometry(profile)

    if not geometry.show_schedule and not geometry.show_priorities:
        notes_title_y = geometry.top_y + 12
        pdf.set_fill_color(theme.TEXT_PRIMARY)
        pdf.set_font(theme.FONT_BOLD, 18)
        pdf.draw_string(geometry.start_x, notes_title_y, "NOTES")

        pdf.set_fill_color(theme.TEXT_SECONDARY)
        pdf.set_font(theme.FONT_REGULAR, 12)
        pdf.draw_right_string(
            geometry.start_x + geometry.total_width, notes_title_y, page_date.isoformat()
        )

        pdf.set_stroke_color(theme.GRID_LINES)
        pdf.set_line_width(1)
        pdf.rect(
            geometry.start_x,
            geometry.bottom_y,
            geometry.total_width,
            geometry.total_height,
            fill=0,
            stroke=1,
        )

        pdf.set_stroke_color(theme.WRITING_LINES)
        pdf.set_line_width(0.35)

        for x_pos in ascending_step_positions(
            start=geometry.start_x,
            end=geometry.start_x + geometry.total_width,
            step=geometry.notes_grid_step,
        ):
            pdf.line(
                x_pos,
                geometry.bottom_y,
                x_pos,
                geometry.bottom_y + geometry.total_height,
            )

        for y_pos in ascending_step_positions(
            start=geometry.bottom_y,
            end=geometry.bottom_y + geometry.total_height,
            step=geometry.notes_grid_step,
        ):
            pdf.line(
                geometry.start_x,
                y_pos,
                geometry.start_x + geometry.total_width,
                y_pos,
            )
        return

    # Left 1/3: schedule blocks with hour-only labels and half-hour subdivisions.
    schedule_x = geometry.schedule_x
    schedule_y = geometry.schedule_y
    schedule_width = geometry.schedule_width
    schedule_height = geometry.schedule_height
    schedule_label_width = geometry.schedule_label_width

    pdf.set_stroke_color(theme.GRID_LINES)
    pdf.set_line_width(1)
    pdf.rect(schedule_x, schedule_y, schedule_width, schedule_height, fill=0, stroke=1)
    pdf.line(
        schedule_x + schedule_label_width,
        schedule_y,
        schedule_x + schedule_label_width,
        schedule_y + schedule_height,
    )

    pdf.set_fill_color(theme.TEXT_PRIMARY)
    pdf.set_font(theme.FONT_BOLD, 18)
    pdf.draw_string(schedule_x, geometry.top_y + 12, "SCHEDULE")

    for hour_idx in range(geometry.schedule_hour_count):
        row = daily_schedule_row_bounds(geometry, hour_idx)
        hour_value = geometry.schedule_start_hour + hour_idx

        pdf.set_fill_color(theme.TEXT_SECONDARY)
        pdf.set_font(theme.FONT_BOLD, 12)
        pdf.draw_centred_string(
            schedule_x + (schedule_label_width / 2),
            row.top - 14,
            f"{hour_value:02d}",
        )

        pdf.set_stroke_color(theme.GRID_LINES)
        pdf.line(schedule_x, row.bottom, schedule_x + schedule_width, row.bottom)

        pdf.set_stroke_color(theme.WRITING_LINES)
        pdf.line(
            schedule_x + schedule_label_width,
            row.center,
            schedule_x + schedule_width,
            row.center,
        )

    # Right 2/3: top quarter priorities checklist, bottom notes with 5mm grid.
    right_x = geometry.right_x
    right_width = geometry.right_width
    priorities_y = geometry.priorities_y
    priorities_height = geometry.priorities_height
    notes_y = geometry.notes_y
    notes_top_y = geometry.notes_top_y
    notes_height = geometry.notes_height

    pdf.set_fill_color(theme.TEXT_PRIMARY)
    pdf.set_font(theme.FONT_BOLD, 18)
    pdf.draw_string(right_x, geometry.top_y + 12, "PRIORITIES")

    pdf.set_stroke_color(theme.GRID_LINES)
    pdf.set_line_width(1)
    pdf.rect(right_x, priorities_y, right_width, priorities_height, fill=0, stroke=1)

    for item_idx in range(geometry.checklist_items):
        row = daily_priorities_row_bounds(geometry, item_idx)

        if item_idx > 0:
            pdf.set_stroke_color(theme.WRITING_LINES)
            pdf.line(right_x, row.top, right_x + right_width, row.top)

        box_x = right_x + 10
        box_y = row.center - (geometry.checklist_box_size / 2)
        pdf.set_stroke_color(theme.ACCENT)
        pdf.rect(
            box_x,
            box_y,
            geometry.checklist_box_size,
            geometry.checklist_box_size,
            fill=0,
            stroke=1,
        )

        pdf.set_stroke_color(theme.WRITING_LINES)
        pdf.line(
            box_x + geometry.checklist_box_size + 12,
            row.center,
            right_x + right_width - 10,
            row.center,
        )
        pdf.line(right_x, row.bottom, right_x + right_width, row.bottom)

    notes_title_y = notes_top_y + 8
    pdf.set_fill_color(theme.TEXT_PRIMARY)
    pdf.set_font(theme.FONT_BOLD, 18)
    pdf.draw_string(right_x, notes_title_y, "NOTES")

    pdf.set_fill_color(theme.TEXT_SECONDARY)
    pdf.set_font(theme.FONT_REGULAR, 12)
    pdf.draw_right_string(right_x + right_width, notes_title_y, page_date.isoformat())

    pdf.set_stroke_color(theme.GRID_LINES)
    pdf.set_line_width(1)
    pdf.rect(right_x, notes_y, right_width, notes_height, fill=0, stroke=1)

    pdf.set_stroke_color(theme.WRITING_LINES)
    pdf.set_line_width(0.35)

    for x_pos in ascending_step_positions(
        start=right_x,
        end=right_x + right_width,
        step=geometry.notes_grid_step,
    ):
        pdf.line(x_pos, notes_y, x_pos, notes_y + notes_height)

    for y_pos in ascending_step_positions(
        start=notes_y,
        end=notes_y + notes_height,
        step=geometry.notes_grid_step,
    ):
        pdf.line(right_x, y_pos, right_x + right_width, y_pos)
