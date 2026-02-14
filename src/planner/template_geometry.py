"""Pure geometry helpers for template renderers."""

from __future__ import annotations

from dataclasses import dataclass

from .profiles import DeviceProfile
from .template_layout import (
    TemplateLayoutProfile,
    font_pt_to_device_units,
    mm_to_device_units,
    pt_to_device_units,
)


@dataclass(frozen=True)
class Rect:
    """Rectangle in device units."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height


@dataclass(frozen=True)
class RowBounds:
    """Top/center/bottom row bounds."""

    top: float
    center: float
    bottom: float


@dataclass(frozen=True)
class ScheduleGeometry:
    """Computed geometry for schedule template body."""

    body: Rect
    hours: tuple[int, ...]
    row_height: float
    hour_col_width: float
    highlight_rect: Rect | None
    hour_font_size: float
    writing_left_padding: float
    writing_right_padding: float


@dataclass(frozen=True)
class DayAtGlanceGeometry:
    """Computed geometry for full day-at-glance template."""

    schedule_left: float
    schedule_right: float
    schedule_width: float
    right_left: float
    right_width: float
    grid_top: float
    bottom: float
    heading_x_offset: float
    schedule_label_max_width: float
    tasks_label_max_width: float
    section_label_min_font: float
    label_col_width: float
    hour_count: int
    row_height: float
    hour_font_size: float
    left_line_padding: float
    right_line_padding: float
    priorities_top: float
    priorities_bottom: float
    priorities_rows_top: float
    priorities_rows: int
    priority_row_height: float
    label_font_size: float
    label_x_offset: float
    task_line_gap: float
    task_box_size: float
    notes_top: float
    notes_rows_top: float
    notes_step: float
    notes_padding: float


@dataclass(frozen=True)
class DayAtGlanceCompactGeometry:
    """Computed geometry for compact day-at-glance template."""

    left: float
    right: float
    content_height: float
    priorities_top: float
    priorities_bottom: float
    schedule_top: float
    schedule_bottom: float
    notes_top: float
    notes_bottom: float
    label_left: float
    label_strip_width: float
    x_padding: float
    section_label_pref: float
    section_label_min: float
    vertical_label_padding: float
    priorities_rows: int
    priorities_row_height: float
    checkbox_size: float
    checkbox_x: float
    text_gap: float
    writing_right: float
    schedule_hours: tuple[int, ...]
    schedule_row_height: float
    hour_font_size: float
    hour_col_width: float
    schedule_line_left_padding: float
    notes_step: float


@dataclass(frozen=True)
class ChecklistGeometry:
    """Computed geometry for checklist-style templates."""

    body: Rect
    rows: int
    row_height: float
    checkbox_col_width: float
    line_padding: float
    box_size: float


def schedule_hours(
    *,
    start_hour: int,
    end_hour: int,
    include_end_hour: bool = False,
) -> tuple[int, ...]:
    """Return schedule hour labels."""
    stop_hour = end_hour + 1 if include_end_hour else end_hour
    hours = tuple(range(start_hour, stop_hour))
    if not hours:
        return (start_hour,)
    return hours


def ascending_step_positions(
    *,
    start: float,
    end: float,
    step: float,
    include_start: bool = False,
    include_end: bool = False,
) -> tuple[float, ...]:
    """Return ascending positions with a fixed step."""
    if step <= 0:
        msg = "step must be positive."
        raise ValueError(msg)

    positions: list[float] = []
    pos = start if include_start else start + step
    epsilon = step * 1e-9
    while pos < end - epsilon or (include_end and abs(pos - end) <= epsilon):
        positions.append(pos)
        pos += step
    return tuple(positions)


def descending_step_positions(
    *,
    start: float,
    end: float,
    step: float,
    include_start: bool = False,
    include_end: bool = False,
) -> tuple[float, ...]:
    """Return descending positions with a fixed step."""
    if step <= 0:
        msg = "step must be positive."
        raise ValueError(msg)

    positions: list[float] = []
    pos = start if include_start else start - step
    epsilon = step * 1e-9
    while pos > end + epsilon or (include_end and abs(pos - end) <= epsilon):
        positions.append(pos)
        pos -= step
    return tuple(positions)


def compute_schedule_geometry(
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    left: float,
    bottom: float,
    right: float,
    header_bottom: float,
    work_start_hour: int,
    work_end_hour: int,
) -> ScheduleGeometry:
    """Compute geometry for the schedule template body."""
    content_height = header_bottom - bottom
    content_width = right - left
    hours = schedule_hours(
        start_hour=layout.schedule_start_hour,
        end_hour=layout.schedule_end_hour,
        include_end_hour=True,
    )
    row_height = content_height / len(hours)
    hour_col_width = min(pt_to_device_units(34, device=device), content_width * 0.2)

    highlight_start = max(layout.schedule_start_hour, work_start_hour)
    highlight_end = min(layout.schedule_end_hour, work_end_hour)
    highlight_rect: Rect | None = None
    if highlight_end >= highlight_start:
        highlight_top = header_bottom - ((highlight_start - layout.schedule_start_hour) * row_height)
        highlight_height = ((highlight_end - highlight_start) + 1) * row_height
        highlight_rect = Rect(
            x=left,
            y=highlight_top - highlight_height,
            width=content_width,
            height=highlight_height,
        )

    return ScheduleGeometry(
        body=Rect(x=left, y=bottom, width=content_width, height=content_height),
        hours=hours,
        row_height=row_height,
        hour_col_width=hour_col_width,
        highlight_rect=highlight_rect,
        hour_font_size=font_pt_to_device_units(9, device=device),
        writing_left_padding=pt_to_device_units(6, device=device),
        writing_right_padding=pt_to_device_units(8, device=device),
    )


def schedule_row_bounds(geometry: ScheduleGeometry, index: int) -> RowBounds:
    """Return row bounds for one schedule hour row."""
    if not 0 <= index < len(geometry.hours):
        msg = f"index must be between 0 and {len(geometry.hours) - 1}."
        raise ValueError(msg)

    row_top = geometry.body.top - (index * geometry.row_height)
    row_bottom = row_top - geometry.row_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.row_height / 2),
        bottom=row_bottom,
    )


def compute_day_at_glance_geometry(
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    left: float,
    bottom: float,
    right: float,
    header_bottom: float,
) -> DayAtGlanceGeometry:
    """Compute geometry for the full day-at-glance layout."""
    content_width = right - left
    gutter = min(18.0, max(8.0, content_width * 0.015))
    schedule_width = content_width * 0.38
    right_width = content_width - schedule_width - gutter
    schedule_left = left
    schedule_right = schedule_left + schedule_width
    right_left = schedule_right + gutter

    heading_x_offset = pt_to_device_units(8, device=device)
    section_heading_band = pt_to_device_units(20, device=device)
    grid_top = header_bottom - section_heading_band
    min_grid_height = pt_to_device_units(180, device=device)
    if (grid_top - bottom) < min_grid_height:
        grid_top = header_bottom - pt_to_device_units(12, device=device)

    label_col_width = min(pt_to_device_units(34, device=device), schedule_width * 0.34)
    hour_count = layout.schedule_end_hour - layout.schedule_start_hour
    schedule_height = grid_top - bottom
    row_height = schedule_height / hour_count

    right_body_height = grid_top - bottom
    priorities_height = right_body_height * 0.35
    priorities_top = grid_top
    priorities_bottom = priorities_top - priorities_height

    priorities_label_band = min(pt_to_device_units(18, device=device), priorities_height * 0.35)
    priorities_rows_top = priorities_top - priorities_label_band
    if priorities_rows_top <= priorities_bottom:
        priorities_rows_top = priorities_top

    priority_row_height = (priorities_rows_top - priorities_bottom) / layout.priorities_rows

    notes_top = priorities_bottom
    notes_height = notes_top - bottom
    notes_label_band = min(pt_to_device_units(18, device=device), notes_height * 0.3)
    notes_rows_top = notes_top - notes_label_band
    if notes_rows_top <= bottom:
        notes_rows_top = notes_top

    return DayAtGlanceGeometry(
        schedule_left=schedule_left,
        schedule_right=schedule_right,
        schedule_width=schedule_width,
        right_left=right_left,
        right_width=right_width,
        grid_top=grid_top,
        bottom=bottom,
        heading_x_offset=heading_x_offset,
        schedule_label_max_width=max(
            schedule_width - (2 * heading_x_offset),
            pt_to_device_units(28, device=device),
        ),
        tasks_label_max_width=max(
            right_width - (2 * heading_x_offset),
            pt_to_device_units(34, device=device),
        ),
        section_label_min_font=font_pt_to_device_units(6, device=device),
        label_col_width=label_col_width,
        hour_count=hour_count,
        row_height=row_height,
        hour_font_size=font_pt_to_device_units(9, device=device),
        left_line_padding=pt_to_device_units(4, device=device),
        right_line_padding=pt_to_device_units(6, device=device),
        priorities_top=priorities_top,
        priorities_bottom=priorities_bottom,
        priorities_rows_top=priorities_rows_top,
        priorities_rows=layout.priorities_rows,
        priority_row_height=priority_row_height,
        label_font_size=font_pt_to_device_units(10, device=device),
        label_x_offset=pt_to_device_units(8, device=device),
        task_line_gap=pt_to_device_units(8, device=device),
        task_box_size=pt_to_device_units(10, device=device),
        notes_top=notes_top,
        notes_rows_top=notes_rows_top,
        notes_step=mm_to_device_units(layout.line_spacing_mm, device=device),
        notes_padding=pt_to_device_units(8, device=device),
    )


def day_at_glance_schedule_row_bounds(geometry: DayAtGlanceGeometry, index: int) -> RowBounds:
    """Return row bounds for one full-layout day-at-glance schedule row."""
    if not 0 <= index < geometry.hour_count:
        msg = f"index must be between 0 and {geometry.hour_count - 1}."
        raise ValueError(msg)

    row_top = geometry.grid_top - (index * geometry.row_height)
    row_bottom = row_top - geometry.row_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.row_height / 2),
        bottom=row_bottom,
    )


def day_at_glance_priorities_row_bounds(geometry: DayAtGlanceGeometry, index: int) -> RowBounds:
    """Return row bounds for one full-layout priorities row."""
    if not 0 <= index < geometry.priorities_rows:
        msg = f"index must be between 0 and {geometry.priorities_rows - 1}."
        raise ValueError(msg)

    row_top = geometry.priorities_rows_top - (index * geometry.priority_row_height)
    row_bottom = row_top - geometry.priority_row_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.priority_row_height / 2),
        bottom=row_bottom,
    )


def compute_day_at_glance_compact_geometry(
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    left: float,
    bottom: float,
    right: float,
    header_bottom: float,
) -> DayAtGlanceCompactGeometry:
    """Compute geometry for the compact day-at-glance layout."""
    content_top = header_bottom
    content_height = content_top - bottom
    x_padding = pt_to_device_units(8, device=device)
    label_strip_width = min(mm_to_device_units(6.0, device=device), (right - left) * 0.14)
    label_left = right - label_strip_width

    priorities_height = content_height * 0.24
    schedule_height = content_height * 0.31
    notes_height = content_height - priorities_height - schedule_height
    min_notes_height = pt_to_device_units(110, device=device)
    if notes_height < min_notes_height:
        deficit = min_notes_height - notes_height
        reduce_from_schedule = min(deficit, schedule_height * 0.20)
        schedule_height -= reduce_from_schedule
        notes_height += reduce_from_schedule

    priorities_top = content_top
    priorities_bottom = priorities_top - priorities_height
    schedule_top = priorities_bottom
    schedule_bottom = schedule_top - schedule_height
    notes_top = schedule_bottom
    notes_bottom = bottom

    schedule_labels = schedule_hours(
        start_hour=layout.schedule_start_hour,
        end_hour=layout.schedule_end_hour,
    )

    return DayAtGlanceCompactGeometry(
        left=left,
        right=right,
        content_height=content_height,
        priorities_top=priorities_top,
        priorities_bottom=priorities_bottom,
        schedule_top=schedule_top,
        schedule_bottom=schedule_bottom,
        notes_top=notes_top,
        notes_bottom=notes_bottom,
        label_left=label_left,
        label_strip_width=label_strip_width,
        x_padding=x_padding,
        section_label_pref=font_pt_to_device_units(10, device=device),
        section_label_min=font_pt_to_device_units(7, device=device),
        vertical_label_padding=mm_to_device_units(1.0, device=device),
        priorities_rows=5,
        priorities_row_height=(priorities_top - priorities_bottom) / 5,
        checkbox_size=pt_to_device_units(10, device=device),
        checkbox_x=left + x_padding,
        text_gap=pt_to_device_units(8, device=device),
        writing_right=label_left - x_padding,
        schedule_hours=schedule_labels,
        schedule_row_height=(schedule_top - schedule_bottom) / len(schedule_labels),
        hour_font_size=font_pt_to_device_units(9, device=device),
        hour_col_width=min(pt_to_device_units(24, device=device), (label_left - left) * 0.18),
        schedule_line_left_padding=pt_to_device_units(6, device=device),
        notes_step=mm_to_device_units(layout.line_spacing_mm, device=device),
    )


def compact_priorities_row_bounds(geometry: DayAtGlanceCompactGeometry, index: int) -> RowBounds:
    """Return row bounds for one compact priorities row."""
    if not 0 <= index < geometry.priorities_rows:
        msg = f"index must be between 0 and {geometry.priorities_rows - 1}."
        raise ValueError(msg)

    row_top = geometry.priorities_top - (index * geometry.priorities_row_height)
    row_bottom = row_top - geometry.priorities_row_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.priorities_row_height / 2),
        bottom=row_bottom,
    )


def compact_schedule_row_bounds(geometry: DayAtGlanceCompactGeometry, index: int) -> RowBounds:
    """Return row bounds for one compact schedule row."""
    if not 0 <= index < len(geometry.schedule_hours):
        msg = f"index must be between 0 and {len(geometry.schedule_hours) - 1}."
        raise ValueError(msg)

    row_top = geometry.schedule_top - (index * geometry.schedule_row_height)
    row_bottom = row_top - geometry.schedule_row_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.schedule_row_height / 2),
        bottom=row_bottom,
    )


def compute_checklist_geometry(
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    left: float,
    bottom: float,
    right: float,
    header_bottom: float,
) -> ChecklistGeometry:
    """Compute geometry for task/todo checklist templates."""
    content_height = header_bottom - bottom
    rows = layout.checklist_rows
    row_height = content_height / rows
    return ChecklistGeometry(
        body=Rect(x=left, y=bottom, width=right - left, height=content_height),
        rows=rows,
        row_height=row_height,
        checkbox_col_width=pt_to_device_units(28, device=device),
        line_padding=pt_to_device_units(8, device=device),
        box_size=min(pt_to_device_units(12.0, device=device), row_height * 0.45),
    )


def checklist_row_bounds(geometry: ChecklistGeometry, index: int) -> RowBounds:
    """Return row bounds for one checklist row."""
    if not 0 <= index < geometry.rows:
        msg = f"index must be between 0 and {geometry.rows - 1}."
        raise ValueError(msg)

    row_top = geometry.body.top - (index * geometry.row_height)
    row_bottom = row_top - geometry.row_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.row_height / 2),
        bottom=row_bottom,
    )
