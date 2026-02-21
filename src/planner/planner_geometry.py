"""Pure geometry helpers for planner page rendering."""

from __future__ import annotations

from dataclasses import dataclass

from .profiles import RenderProfile

_POINTS_PER_MM = 72.0 / 25.4


@dataclass(frozen=True)
class Point:
    """2D point in page units."""

    x: float
    y: float


@dataclass(frozen=True)
class Rect:
    """Rectangle in page units."""

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
class MonthGridGeometry:
    """Resolved geometry for the monthly calendar grid."""

    start_x: float
    start_y: float
    width: float
    height: float
    col_width: float
    row_height: float
    weekday_label_y_offset: float = 20.0


@dataclass(frozen=True)
class WeekGridGeometry:
    """Resolved geometry for the weekly page grid."""

    start_x: float
    start_y: float
    width: float
    height: float
    col_width: float
    label_margin: float = 8.0
    label_height: float = 56.0
    label_top_offset: float = 10.0
    writing_line_top_offset: float = 82.0
    writing_line_bottom_margin: float = 16.0
    writing_line_horizontal_margin: float = 8.0
    writing_line_step: float = 30.0


@dataclass(frozen=True)
class DailyViewGeometry:
    """Resolved geometry for the daily page."""

    start_x: float
    top_y: float
    bottom_y: float
    total_width: float
    total_height: float
    show_schedule: bool
    show_priorities: bool
    notes_grid_step: float
    schedule_width: float
    section_gutter: float
    right_x: float
    right_width: float
    schedule_label_width: float
    schedule_x: float
    schedule_y: float
    schedule_height: float
    schedule_start_hour: int
    schedule_end_hour: int
    schedule_hour_count: int
    schedule_hour_height: float
    priorities_height: float
    priorities_y: float
    notes_y: float
    section_gap: float
    notes_top_y: float
    notes_height: float
    checklist_items: int
    checklist_item_height: float
    checklist_box_size: float


@dataclass(frozen=True)
class RowBounds:
    """Vertical row bounds with center point."""

    top: float
    center: float
    bottom: float


def mm_to_points(value_mm: float) -> float:
    """Convert millimeters into page points."""
    return value_mm * _POINTS_PER_MM


def compute_month_grid_geometry(profile: RenderProfile) -> MonthGridGeometry:
    """Compute monthly grid bounds and cell sizes."""
    month_profile = profile.layout.month
    start_x = profile.sidebar_width + month_profile.side_padding
    start_y = profile.page_height - profile.header_height - month_profile.top_padding
    width = profile.page_width - profile.sidebar_width - (2 * month_profile.side_padding)
    height = profile.page_height - profile.header_height - month_profile.bottom_padding
    return MonthGridGeometry(
        start_x=start_x,
        start_y=start_y,
        width=width,
        height=height,
        col_width=width / 7,
        row_height=height / 6,
    )


def month_weekday_label_center(geometry: MonthGridGeometry, col_idx: int) -> Point:
    """Return center point for a month weekday label."""
    if not 0 <= col_idx <= 6:
        msg = "col_idx must be between 0 and 6."
        raise ValueError(msg)
    return Point(
        x=geometry.start_x + (col_idx * geometry.col_width) + (geometry.col_width / 2),
        y=geometry.start_y + geometry.weekday_label_y_offset,
    )


def month_cell_rect(geometry: MonthGridGeometry, row_idx: int, col_idx: int) -> Rect:
    """Return one month cell rectangle."""
    if not 0 <= row_idx <= 5:
        msg = "row_idx must be between 0 and 5."
        raise ValueError(msg)
    if not 0 <= col_idx <= 6:
        msg = "col_idx must be between 0 and 6."
        raise ValueError(msg)
    return Rect(
        x=geometry.start_x + (col_idx * geometry.col_width),
        y=geometry.start_y - ((row_idx + 1) * geometry.row_height),
        width=geometry.col_width,
        height=geometry.row_height,
    )


def month_week_label_rect(
    geometry: MonthGridGeometry,
    row_idx: int,
    *,
    label_width: float,
    label_gap: float,
) -> Rect:
    """Return the side week-label rectangle for one month row."""
    if label_width <= 0:
        msg = "label_width must be positive."
        raise ValueError(msg)
    cell = month_cell_rect(geometry, row_idx, 0)
    return Rect(
        x=geometry.start_x - label_width - label_gap,
        y=cell.y,
        width=label_width,
        height=geometry.row_height,
    )


def month_day_badge_rect(
    cell: Rect,
    *,
    box_height: float,
    box_max_width: float,
) -> Rect:
    """Return the day-number badge rectangle inside a month cell."""
    if box_height <= 0:
        msg = "box_height must be positive."
        raise ValueError(msg)
    if box_max_width <= 0:
        msg = "box_max_width must be positive."
        raise ValueError(msg)
    return Rect(
        x=cell.x,
        y=cell.y + cell.height - box_height,
        width=min(box_max_width, cell.width),
        height=box_height,
    )


def month_writing_line_points(cell: Rect, *, margin: float) -> tuple[Point, Point]:
    """Return endpoints for the optional month cell writing line."""
    line_y = cell.y + (cell.height / 2)
    return (
        Point(x=cell.x + margin, y=line_y),
        Point(x=cell.right - margin, y=line_y),
    )


def compute_week_grid_geometry(profile: RenderProfile, *, column_count: int) -> WeekGridGeometry:
    """Compute weekly grid bounds and per-column geometry."""
    if column_count < 1:
        msg = "column_count must be >= 1."
        raise ValueError(msg)

    start_x = profile.sidebar_width + 40
    start_y = profile.page_height - profile.header_height - 80
    width = profile.page_width - profile.sidebar_width - 80
    height = profile.page_height - profile.header_height - 260
    return WeekGridGeometry(
        start_x=start_x,
        start_y=start_y,
        width=width,
        height=height,
        col_width=width / column_count,
    )


def week_column_rect(geometry: WeekGridGeometry, col_idx: int) -> Rect:
    """Return one weekly day column rectangle."""
    if col_idx < 0:
        msg = "col_idx must be >= 0."
        raise ValueError(msg)
    return Rect(
        x=geometry.start_x + (col_idx * geometry.col_width),
        y=geometry.start_y - geometry.height,
        width=geometry.col_width,
        height=geometry.height,
    )


def week_day_label_rect(geometry: WeekGridGeometry, *, column: Rect) -> Rect:
    """Return day-number label badge rect inside a weekly column."""
    label_width = column.width - (2 * geometry.label_margin)
    label_top = geometry.start_y - geometry.label_top_offset
    return Rect(
        x=column.x + geometry.label_margin,
        y=label_top - geometry.label_height,
        width=label_width,
        height=geometry.label_height,
    )


def week_writing_line_y_positions(geometry: WeekGridGeometry, *, column: Rect) -> tuple[float, ...]:
    """Return y positions for weekly writing lines."""
    positions: list[float] = []
    line_y = geometry.start_y - geometry.writing_line_top_offset
    min_y = column.y + geometry.writing_line_bottom_margin
    while line_y >= min_y:
        positions.append(line_y)
        line_y -= geometry.writing_line_step
    return tuple(positions)


def compute_daily_view_geometry(profile: RenderProfile) -> DailyViewGeometry:
    """Compute shared daily page geometry for both compact/full layouts."""
    daily_profile = profile.layout.daily
    start_x = profile.sidebar_width + 40
    top_y = profile.page_height - profile.header_height - 90
    bottom_y = 110
    total_width = profile.page_width - profile.sidebar_width - 80
    total_height = top_y - bottom_y

    schedule_width = total_width / 3
    section_gutter = 16
    right_x = start_x + schedule_width + section_gutter
    right_width = total_width - schedule_width - section_gutter

    schedule_label_width = 42
    schedule_x = start_x
    schedule_y = bottom_y
    schedule_height = total_height
    schedule_start_hour = 6
    schedule_end_hour = 22
    schedule_hour_count = schedule_end_hour - schedule_start_hour
    schedule_hour_height = schedule_height / schedule_hour_count

    priorities_height = total_height * 0.25
    priorities_y = top_y - priorities_height
    notes_y = bottom_y
    section_gap = 28
    notes_top_y = priorities_y - section_gap
    notes_height = notes_top_y - notes_y
    checklist_items = 6

    return DailyViewGeometry(
        start_x=start_x,
        top_y=top_y,
        bottom_y=bottom_y,
        total_width=total_width,
        total_height=total_height,
        show_schedule=daily_profile.show_schedule,
        show_priorities=daily_profile.show_priorities,
        notes_grid_step=mm_to_points(daily_profile.notes_grid_step_mm),
        schedule_width=schedule_width,
        section_gutter=section_gutter,
        right_x=right_x,
        right_width=right_width,
        schedule_label_width=schedule_label_width,
        schedule_x=schedule_x,
        schedule_y=schedule_y,
        schedule_height=schedule_height,
        schedule_start_hour=schedule_start_hour,
        schedule_end_hour=schedule_end_hour,
        schedule_hour_count=schedule_hour_count,
        schedule_hour_height=schedule_hour_height,
        priorities_height=priorities_height,
        priorities_y=priorities_y,
        notes_y=notes_y,
        section_gap=section_gap,
        notes_top_y=notes_top_y,
        notes_height=notes_height,
        checklist_items=checklist_items,
        checklist_item_height=priorities_height / checklist_items,
        checklist_box_size=13,
    )


def daily_schedule_row_bounds(geometry: DailyViewGeometry, hour_idx: int) -> RowBounds:
    """Return top/center/bottom bounds for one schedule row."""
    if not 0 <= hour_idx < geometry.schedule_hour_count:
        msg = f"hour_idx must be between 0 and {geometry.schedule_hour_count - 1}."
        raise ValueError(msg)
    row_top = geometry.top_y - (hour_idx * geometry.schedule_hour_height)
    row_bottom = row_top - geometry.schedule_hour_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.schedule_hour_height / 2),
        bottom=row_bottom,
    )


def daily_priorities_row_bounds(geometry: DailyViewGeometry, item_idx: int) -> RowBounds:
    """Return top/center/bottom bounds for one priorities row."""
    if not 0 <= item_idx < geometry.checklist_items:
        msg = f"item_idx must be between 0 and {geometry.checklist_items - 1}."
        raise ValueError(msg)
    row_top = (
        geometry.priorities_y
        + geometry.priorities_height
        - (item_idx * geometry.checklist_item_height)
    )
    row_bottom = row_top - geometry.checklist_item_height
    return RowBounds(
        top=row_top,
        center=row_top - (geometry.checklist_item_height / 2),
        bottom=row_bottom,
    )


def ascending_step_positions(*, start: float, end: float, step: float) -> tuple[float, ...]:
    """Return monotonically increasing positions between two bounds."""
    if step <= 0:
        msg = "step must be positive."
        raise ValueError(msg)
    positions: list[float] = []
    pos = start + step
    while pos < end:
        positions.append(pos)
        pos += step
    return tuple(positions)
