"""Template drawing renderers and style helpers."""

from __future__ import annotations

from collections.abc import Sequence

from .config import Theme
from .drawing import DrawingPrimitives
from .profiles import DeviceProfile
from .template_geometry import (
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
from .template_layout import (
    TemplateLayoutProfile,
    content_bounds,
    font_pt_to_device_units,
    mm_to_device_units,
    pt_to_device_units,
)

NOTES_FILL_TYPES = ("lines", "grid", "dotted-grid", "millimeter")

SCHEDULE_TEMPLATE_WORK_START_HOUR = 9
SCHEDULE_TEMPLATE_WORK_END_HOUR = 18

TEMPLATE_BORDER_WIDTH_MM = 0.22
TEMPLATE_RULE_WIDTH_MM = 0.16
TEMPLATE_FINE_RULE_WIDTH_MM = 0.12
TEMPLATE_DIVIDER_WIDTH_MM = 0.32


def _apply_border_stroke(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    theme: type = Theme,
) -> None:
    pdf.set_stroke_color(theme.TEXT_SECONDARY)
    pdf.set_line_width(mm_to_device_units(TEMPLATE_BORDER_WIDTH_MM, device=device))


def _apply_rule_stroke(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    theme: type = Theme,
) -> None:
    pdf.set_stroke_color(theme.GRID_LINES)
    pdf.set_line_width(mm_to_device_units(TEMPLATE_RULE_WIDTH_MM, device=device))


def _apply_fine_rule_stroke(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    theme: type = Theme,
) -> None:
    pdf.set_stroke_color(theme.GRID_LINES)
    pdf.set_line_width(mm_to_device_units(TEMPLATE_FINE_RULE_WIDTH_MM, device=device))


def _apply_divider_stroke(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    theme: type = Theme,
) -> None:
    pdf.set_stroke_color(theme.TEXT_SECONDARY)
    pdf.set_line_width(mm_to_device_units(TEMPLATE_DIVIDER_WIDTH_MM, device=device))


def _band_label_baseline(*, top: float, bottom: float, font_size: float) -> float:
    """Return a baseline that visually centers text inside a vertical band."""
    band_height = top - bottom
    return bottom + ((band_height - font_size) / 2) + (font_size * 0.2)


def _fit_font_size_to_width(
    pdf: DrawingPrimitives,
    *,
    text: str,
    font_name: str,
    preferred_size: float,
    min_size: float,
    max_width: float,
) -> float:
    """Return a font size that keeps text width within max_width."""
    if max_width <= 0:
        return min_size

    size = preferred_size
    while size > min_size and pdf.string_width(text, font_name, size) > max_width:
        size -= 0.5
    if size < min_size:
        return min_size
    return size


def _pick_fitting_label(
    pdf: DrawingPrimitives,
    *,
    candidates: Sequence[str],
    font_name: str,
    preferred_size: float,
    min_size: float,
    max_width: float,
) -> tuple[str, float]:
    """Pick the first label candidate that fits the available width."""
    fallback_label = candidates[-1]
    fallback_size = _fit_font_size_to_width(
        pdf,
        text=fallback_label,
        font_name=font_name,
        preferred_size=preferred_size,
        min_size=min_size,
        max_width=max_width,
    )

    for label in candidates:
        fitted_size = _fit_font_size_to_width(
            pdf,
            text=label,
            font_name=font_name,
            preferred_size=preferred_size,
            min_size=min_size,
            max_width=max_width,
        )
        if pdf.string_width(label, font_name, fitted_size) <= max_width:
            return (label, fitted_size)
    return (fallback_label, fallback_size)


def _title_candidates(title: str) -> tuple[str, ...]:
    """Return progressively shorter title candidates."""
    variants: list[str] = [title]
    if " AT A " in title:
        variants.append(title.replace(" AT A ", " "))
    if " & " in title:
        variants.append(title.replace(" & ", "/"))
    if " " in title:
        variants.append(title.replace(" ", ""))

    deduped: list[str] = []
    for variant in variants:
        if variant not in deduped:
            deduped.append(variant)
    return tuple(deduped)


def draw_page_background(
    pdf: DrawingPrimitives,
    device: DeviceProfile,
    *,
    theme: type = Theme,
) -> None:
    pdf.set_fill_color(theme.BACKGROUND)
    pdf.rect(0, 0, device.page_width, device.page_height, fill=1, stroke=0)


def _draw_header(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    left: float,
    right: float,
    top: float,
    header_height: float,
    title: str,
    theme: type = Theme,
) -> float:
    if header_height <= 0:
        return top

    header_bottom = top - header_height
    _apply_border_stroke(pdf, device=device, theme=theme)
    pdf.line(left, header_bottom, right, header_bottom)

    content_width = right - left
    date_line_width = max(
        pt_to_device_units(24, device=device),
        min(pt_to_device_units(72, device=device), content_width * 0.22),
    )
    label_gap = pt_to_device_units(8, device=device)
    title_date_gap = pt_to_device_units(10, device=device)

    date_label, date_font_size = _pick_fitting_label(
        pdf,
        candidates=("DATE", "DT"),
        font_name=theme.FONT_BOLD,
        preferred_size=font_pt_to_device_units(10, device=device),
        min_size=font_pt_to_device_units(6, device=device),
        max_width=max(content_width * 0.16, pt_to_device_units(22, device=device)),
    )
    label_width = pdf.string_width(date_label, theme.FONT_BOLD, date_font_size)
    date_block_width = label_width + label_gap + date_line_width
    title_max_width = max(content_width - date_block_width - title_date_gap, content_width * 0.35)
    title_label, title_font_size = _pick_fitting_label(
        pdf,
        candidates=_title_candidates(title),
        font_name=theme.FONT_BOLD,
        preferred_size=font_pt_to_device_units(12, device=device),
        min_size=font_pt_to_device_units(7, device=device),
        max_width=title_max_width,
    )

    pdf.set_fill_color(theme.TEXT_PRIMARY)
    pdf.set_font(theme.FONT_BOLD, title_font_size)
    text_y = header_bottom + (header_height * 0.42)
    pdf.draw_string(left, text_y, title_label)

    pdf.set_fill_color(theme.TEXT_SECONDARY)
    pdf.set_font(theme.FONT_BOLD, date_font_size)
    line_right = right
    line_left = line_right - date_line_width
    pdf.draw_string(line_left - label_width - label_gap, text_y, date_label)
    _apply_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(line_left, text_y, line_right, text_y)
    return header_bottom


def _draw_lines_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title="LINES",
        theme=theme,
    )

    _apply_rule_stroke(pdf, device=device, theme=theme)
    step = mm_to_device_units(layout.line_spacing_mm, device=device)
    for y_pos in descending_step_positions(
        start=header_bottom,
        end=bottom,
        step=step,
        include_end=True,
    ):
        pdf.line(left, y_pos, right, y_pos)


def _draw_grid_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title="GRID",
        theme=theme,
    )

    step = mm_to_device_units(layout.grid_spacing_mm, device=device)
    _apply_fine_rule_stroke(pdf, device=device, theme=theme)

    for x_pos in ascending_step_positions(
        start=left,
        end=right,
        step=step,
        include_start=True,
        include_end=True,
    ):
        pdf.line(x_pos, bottom, x_pos, header_bottom)

    for y_pos in descending_step_positions(
        start=header_bottom,
        end=bottom,
        step=step,
        include_start=True,
        include_end=True,
    ):
        pdf.line(left, y_pos, right, y_pos)


def _draw_dotted_grid_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title="DOTTED GRID",
        theme=theme,
    )

    x_step = mm_to_device_units(layout.dot_spacing_mm, device=device)
    y_step = mm_to_device_units(layout.dot_spacing_mm, device=device)
    dot_radius = mm_to_device_units(layout.dot_radius_mm, device=device)

    pdf.set_fill_color(theme.GRID_LINES)
    for y_pos in ascending_step_positions(
        start=bottom,
        end=header_bottom,
        step=y_step,
        include_start=True,
        include_end=True,
    ):
        for x_pos in ascending_step_positions(
            start=left,
            end=right,
            step=x_step,
            include_start=True,
            include_end=True,
        ):
            pdf.circle(x_pos, y_pos, dot_radius, fill=1, stroke=0)


def _draw_schedule_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title="SCHEDULE",
        theme=theme,
    )

    geometry = compute_schedule_geometry(
        device=device,
        layout=layout,
        left=left,
        bottom=bottom,
        right=right,
        header_bottom=header_bottom,
        work_start_hour=SCHEDULE_TEMPLATE_WORK_START_HOUR,
        work_end_hour=SCHEDULE_TEMPLATE_WORK_END_HOUR,
    )
    _apply_border_stroke(pdf, device=device, theme=theme)
    pdf.rect(
        geometry.body.x,
        geometry.body.y,
        geometry.body.width,
        geometry.body.height,
        fill=0,
        stroke=1,
    )

    if geometry.highlight_rect is not None:
        pdf.set_fill_color(theme.LINK_BADGE_BG)
        pdf.rect(
            geometry.highlight_rect.x,
            geometry.highlight_rect.y,
            geometry.highlight_rect.width,
            geometry.highlight_rect.height,
            fill=1,
            stroke=0,
        )

    _apply_rule_stroke(pdf, device=device, theme=theme)
    hour_col_x = geometry.body.x + geometry.hour_col_width
    pdf.line(hour_col_x, geometry.body.y, hour_col_x, geometry.body.top)

    for idx, hour_value in enumerate(geometry.hours):
        row = schedule_row_bounds(geometry, idx)

        if idx > 0:
            _apply_rule_stroke(pdf, device=device, theme=theme)
            pdf.line(geometry.body.x, row.top, geometry.body.right, row.top)

        pdf.set_fill_color(theme.TEXT_SECONDARY)
        pdf.set_font(theme.FONT_BOLD, geometry.hour_font_size)
        pdf.draw_centred_string(
            geometry.body.x + (geometry.hour_col_width / 2),
            row.center - (geometry.hour_font_size * 0.33),
            f"{hour_value:02d}",
        )

        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        pdf.line(
            geometry.body.x + geometry.hour_col_width + geometry.writing_left_padding,
            row.center,
            geometry.body.right - geometry.writing_right_padding,
            row.center,
        )
        pdf.line(geometry.body.x, row.bottom, geometry.body.right, row.bottom)


def _draw_day_at_glance_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    if device.compact_day_at_glance:
        _draw_day_at_glance_compact_template(pdf, device=device, layout=layout, theme=theme)
        return

    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title="DAY AT A GLANCE",
        theme=theme,
    )

    geometry = compute_day_at_glance_geometry(
        device=device,
        layout=layout,
        left=left,
        bottom=bottom,
        right=right,
        header_bottom=header_bottom,
    )

    _apply_border_stroke(pdf, device=device, theme=theme)
    pdf.rect(
        geometry.schedule_left,
        geometry.bottom,
        geometry.schedule_width,
        header_bottom - geometry.bottom,
        fill=0,
        stroke=1,
    )
    pdf.rect(
        geometry.right_left,
        geometry.bottom,
        geometry.right_width,
        header_bottom - geometry.bottom,
        fill=0,
        stroke=1,
    )

    schedule_label, schedule_font_size = _pick_fitting_label(
        pdf,
        candidates=("SCHEDULE", "SCHED"),
        font_name=theme.FONT_BOLD,
        preferred_size=font_pt_to_device_units(11, device=device),
        min_size=geometry.section_label_min_font,
        max_width=geometry.schedule_label_max_width,
    )
    tasks_label, tasks_font_size = _pick_fitting_label(
        pdf,
        candidates=("TASKS & NOTES", "TASKS/NOTES", "TASKS"),
        font_name=theme.FONT_BOLD,
        preferred_size=font_pt_to_device_units(11, device=device),
        min_size=geometry.section_label_min_font,
        max_width=geometry.tasks_label_max_width,
    )
    schedule_label_y = _band_label_baseline(
        top=header_bottom,
        bottom=geometry.grid_top,
        font_size=schedule_font_size,
    )
    tasks_label_y = _band_label_baseline(
        top=header_bottom,
        bottom=geometry.grid_top,
        font_size=tasks_font_size,
    )

    pdf.set_fill_color(theme.TEXT_PRIMARY)
    pdf.set_font(theme.FONT_BOLD, schedule_font_size)
    pdf.draw_string(
        geometry.schedule_left + geometry.heading_x_offset,
        schedule_label_y,
        schedule_label,
    )
    pdf.set_font(theme.FONT_BOLD, tasks_font_size)
    pdf.draw_string(
        geometry.right_left + geometry.heading_x_offset,
        tasks_label_y,
        tasks_label,
    )

    _apply_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(geometry.schedule_left, geometry.grid_top, geometry.schedule_right, geometry.grid_top)
    pdf.line(geometry.right_left, geometry.grid_top, right, geometry.grid_top)

    _apply_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(
        geometry.schedule_left + geometry.label_col_width,
        geometry.bottom,
        geometry.schedule_left + geometry.label_col_width,
        geometry.grid_top,
    )

    for idx in range(geometry.hour_count):
        row = day_at_glance_schedule_row_bounds(geometry, idx)
        hour_value = layout.schedule_start_hour + idx

        if idx > 0:
            _apply_rule_stroke(pdf, device=device, theme=theme)
            pdf.line(geometry.schedule_left, row.top, geometry.schedule_right, row.top)

        pdf.set_fill_color(theme.TEXT_SECONDARY)
        pdf.set_font(theme.FONT_BOLD, geometry.hour_font_size)
        pdf.draw_centred_string(
            geometry.schedule_left + (geometry.label_col_width / 2),
            row.center - (geometry.hour_font_size * 0.33),
            f"{hour_value:02d}",
        )

        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        pdf.line(
            geometry.schedule_left + geometry.label_col_width + geometry.left_line_padding,
            row.center,
            geometry.schedule_right - geometry.right_line_padding,
            row.center,
        )
        pdf.line(geometry.schedule_left, row.bottom, geometry.schedule_right, row.bottom)

    _apply_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(geometry.right_left, geometry.priorities_bottom, right, geometry.priorities_bottom)
    pdf.set_fill_color(theme.TEXT_SECONDARY)
    pdf.set_font(theme.FONT_BOLD, geometry.label_font_size)
    priorities_label_y = _band_label_baseline(
        top=geometry.priorities_top,
        bottom=geometry.priorities_rows_top,
        font_size=geometry.label_font_size,
    )
    pdf.draw_string(
        geometry.right_left + geometry.label_x_offset,
        priorities_label_y,
        "TOP PRIORITIES",
    )
    _apply_fine_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(geometry.right_left, geometry.priorities_rows_top, right, geometry.priorities_rows_top)

    for idx in range(geometry.priorities_rows):
        row = day_at_glance_priorities_row_bounds(geometry, idx)
        if idx > 0:
            _apply_fine_rule_stroke(pdf, device=device, theme=theme)
            pdf.line(geometry.right_left, row.top, right, row.top)

        box_x = geometry.right_left + geometry.label_x_offset
        box_y = row.center - (geometry.task_box_size / 2)
        pdf.set_stroke_color(theme.ACCENT)
        pdf.set_line_width(mm_to_device_units(TEMPLATE_RULE_WIDTH_MM, device=device))
        pdf.rect(box_x, box_y, geometry.task_box_size, geometry.task_box_size, fill=0, stroke=1)

        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        pdf.line(
            box_x + geometry.task_box_size + geometry.task_line_gap,
            row.center,
            right - geometry.task_line_gap,
            row.center,
        )
        pdf.line(geometry.right_left, row.bottom, right, row.bottom)

    pdf.set_fill_color(theme.TEXT_SECONDARY)
    pdf.set_font(theme.FONT_BOLD, geometry.label_font_size)
    notes_label_y = _band_label_baseline(
        top=geometry.notes_top,
        bottom=geometry.notes_rows_top,
        font_size=geometry.label_font_size,
    )
    pdf.draw_string(geometry.right_left + geometry.label_x_offset, notes_label_y, "NOTES")
    _apply_fine_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(geometry.right_left, geometry.notes_rows_top, right, geometry.notes_rows_top)

    _apply_rule_stroke(pdf, device=device, theme=theme)
    for y_pos in descending_step_positions(
        start=geometry.notes_rows_top,
        end=geometry.bottom,
        step=geometry.notes_step,
        include_end=True,
    ):
        pdf.line(
            geometry.right_left + geometry.notes_padding,
            y_pos,
            right - geometry.notes_padding,
            y_pos,
        )


def _draw_day_at_glance_compact_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title="DAY AT A GLANCE",
        theme=theme,
    )

    geometry = compute_day_at_glance_compact_geometry(
        device=device,
        layout=layout,
        left=left,
        bottom=bottom,
        right=right,
        header_bottom=header_bottom,
    )

    _apply_border_stroke(pdf, device=device, theme=theme)
    pdf.rect(left, geometry.notes_bottom, right - left, geometry.content_height, fill=0, stroke=1)

    _apply_divider_stroke(pdf, device=device, theme=theme)
    pdf.line(left, geometry.priorities_bottom, right, geometry.priorities_bottom)
    pdf.line(left, geometry.schedule_bottom, right, geometry.schedule_bottom)

    _apply_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(
        geometry.label_left,
        geometry.priorities_bottom,
        geometry.label_left,
        geometry.priorities_top,
    )
    pdf.line(
        geometry.label_left, geometry.schedule_bottom, geometry.label_left, geometry.schedule_top
    )
    pdf.line(geometry.label_left, geometry.notes_bottom, geometry.label_left, geometry.notes_top)

    def draw_vertical_section_label(
        *,
        section_top: float,
        section_bottom: float,
        label_candidates: Sequence[str],
    ) -> None:
        section_height = section_top - section_bottom
        label, label_size = _pick_fitting_label(
            pdf,
            candidates=label_candidates,
            font_name=theme.FONT_BOLD,
            preferred_size=geometry.section_label_pref,
            min_size=geometry.section_label_min,
            max_width=max(
                section_height - (2 * geometry.vertical_label_padding),
                pt_to_device_units(40, device=device),
            ),
        )
        center_x = geometry.label_left + (geometry.label_strip_width / 2)
        center_y = section_bottom + (section_height / 2)
        pdf.save_state()
        pdf.set_fill_color(theme.TEXT_SECONDARY)
        pdf.set_font(theme.FONT_BOLD, label_size)
        pdf.translate(center_x, center_y)
        pdf.rotate(90)
        pdf.draw_centred_string(0, -(label_size * 0.33), label)
        pdf.restore_state()

    draw_vertical_section_label(
        section_top=geometry.priorities_top,
        section_bottom=geometry.priorities_bottom,
        label_candidates=("TOP PRIORITIES", "PRIORITIES"),
    )
    draw_vertical_section_label(
        section_top=geometry.schedule_top,
        section_bottom=geometry.schedule_bottom,
        label_candidates=("SCHEDULE", "SCHED"),
    )
    draw_vertical_section_label(
        section_top=geometry.notes_top,
        section_bottom=geometry.notes_bottom,
        label_candidates=("NOTES",),
    )

    for idx in range(geometry.priorities_rows):
        row = compact_priorities_row_bounds(geometry, idx)

        if idx > 0:
            _apply_fine_rule_stroke(pdf, device=device, theme=theme)
            pdf.line(left, row.top, geometry.label_left, row.top)

        box_y = row.center - (geometry.checkbox_size / 2)
        pdf.set_stroke_color(theme.ACCENT)
        pdf.set_line_width(mm_to_device_units(TEMPLATE_RULE_WIDTH_MM, device=device))
        pdf.rect(
            geometry.checkbox_x,
            box_y,
            geometry.checkbox_size,
            geometry.checkbox_size,
            fill=0,
            stroke=1,
        )

        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        line_start_x = geometry.checkbox_x + geometry.checkbox_size + geometry.text_gap
        pdf.line(line_start_x, row.center, geometry.writing_right, row.center)
        pdf.line(left, row.bottom, geometry.label_left, row.bottom)

    _apply_rule_stroke(pdf, device=device, theme=theme)
    pdf.line(
        left + geometry.hour_col_width,
        geometry.schedule_bottom,
        left + geometry.hour_col_width,
        geometry.schedule_top,
    )

    for idx, hour_value in enumerate(geometry.schedule_hours):
        row = compact_schedule_row_bounds(geometry, idx)

        if idx > 0:
            _apply_rule_stroke(pdf, device=device, theme=theme)
            pdf.line(left, row.top, geometry.label_left, row.top)

        pdf.set_fill_color(theme.TEXT_SECONDARY)
        pdf.set_font(theme.FONT_BOLD, geometry.hour_font_size)
        pdf.draw_centred_string(
            left + (geometry.hour_col_width / 2),
            row.center - (geometry.hour_font_size * 0.33),
            f"{hour_value:02d}",
        )

        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        line_left = left + geometry.hour_col_width + geometry.schedule_line_left_padding
        pdf.line(line_left, row.center, geometry.writing_right, row.center)
        pdf.line(left, row.bottom, geometry.label_left, row.bottom)

    _apply_rule_stroke(pdf, device=device, theme=theme)
    for y_pos in descending_step_positions(
        start=geometry.notes_top,
        end=geometry.notes_bottom,
        step=geometry.notes_step,
        include_end=True,
    ):
        pdf.line(left + geometry.x_padding, y_pos, geometry.writing_right, y_pos)


def _draw_checklist_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    title: str,
    theme: type = Theme,
) -> None:
    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title=title,
        theme=theme,
    )

    geometry = compute_checklist_geometry(
        device=device,
        layout=layout,
        left=left,
        bottom=bottom,
        right=right,
        header_bottom=header_bottom,
    )

    _apply_border_stroke(pdf, device=device, theme=theme)
    pdf.rect(
        geometry.body.x,
        geometry.body.y,
        geometry.body.width,
        geometry.body.height,
        fill=0,
        stroke=1,
    )
    pdf.line(
        geometry.body.x + geometry.checkbox_col_width,
        geometry.body.y,
        geometry.body.x + geometry.checkbox_col_width,
        geometry.body.top,
    )

    for idx in range(geometry.rows):
        row = checklist_row_bounds(geometry, idx)

        if idx > 0:
            _apply_fine_rule_stroke(pdf, device=device, theme=theme)
            pdf.line(geometry.body.x, row.top, geometry.body.right, row.top)

        box_x = geometry.body.x + ((geometry.checkbox_col_width - geometry.box_size) / 2)
        box_y = row.center - (geometry.box_size / 2)
        pdf.set_stroke_color(theme.ACCENT)
        pdf.set_line_width(mm_to_device_units(TEMPLATE_RULE_WIDTH_MM, device=device))
        pdf.rect(box_x, box_y, geometry.box_size, geometry.box_size, fill=0, stroke=1)

        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        pdf.line(
            geometry.body.x + geometry.checkbox_col_width + geometry.line_padding,
            row.center,
            geometry.body.right - geometry.line_padding,
            row.center,
        )
        pdf.line(geometry.body.x, row.bottom, geometry.body.right, row.bottom)


def _draw_task_list_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    _draw_checklist_template(pdf, device=device, layout=layout, title="TASK LIST", theme=theme)


def _draw_notes_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    notes_fill: str = "lines",
    theme: type = Theme,
) -> None:
    left, bottom, right, top = content_bounds(device, layout)
    header_bottom = _draw_header(
        pdf,
        device=device,
        left=left,
        right=right,
        top=top,
        header_height=mm_to_device_units(layout.header_height_mm, device=device),
        title="NOTES",
        theme=theme,
    )

    content_height = header_bottom - bottom
    _apply_border_stroke(pdf, device=device, theme=theme)
    pdf.rect(left, bottom, right - left, content_height, fill=0, stroke=1)

    if notes_fill == "lines":
        step = mm_to_device_units(layout.line_spacing_mm, device=device)
        line_padding = pt_to_device_units(8, device=device)
        _apply_rule_stroke(pdf, device=device, theme=theme)
        for y_pos in descending_step_positions(
            start=header_bottom,
            end=bottom,
            step=step,
            include_end=True,
        ):
            pdf.line(left + line_padding, y_pos, right - line_padding, y_pos)
        return

    if notes_fill == "grid":
        step = mm_to_device_units(layout.grid_spacing_mm, device=device)
        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        for x_pos in ascending_step_positions(
            start=left,
            end=right,
            step=step,
        ):
            pdf.line(x_pos, bottom, x_pos, header_bottom)
        for y_pos in ascending_step_positions(
            start=bottom,
            end=header_bottom,
            step=step,
        ):
            pdf.line(left, y_pos, right, y_pos)
        return

    if notes_fill == "dotted-grid":
        x_step = mm_to_device_units(layout.dot_spacing_mm, device=device)
        y_step = mm_to_device_units(layout.dot_spacing_mm, device=device)
        dot_radius = mm_to_device_units(layout.dot_radius_mm, device=device)
        pdf.set_fill_color(theme.GRID_LINES)
        for y_pos in ascending_step_positions(
            start=bottom,
            end=header_bottom,
            step=y_step,
        ):
            for x_pos in ascending_step_positions(
                start=left,
                end=right,
                step=x_step,
            ):
                pdf.circle(x_pos, y_pos, dot_radius, fill=1, stroke=0)
        return

    if notes_fill == "millimeter":
        minor_step = mm_to_device_units(1.0, device=device)
        major_every = 5

        _apply_fine_rule_stroke(pdf, device=device, theme=theme)
        x_pos = left + minor_step
        x_idx = 1
        while x_pos < right:
            if x_idx % major_every != 0:
                pdf.line(x_pos, bottom, x_pos, header_bottom)
            x_pos += minor_step
            x_idx += 1

        y_pos = bottom + minor_step
        y_idx = 1
        while y_pos < header_bottom:
            if y_idx % major_every != 0:
                pdf.line(left, y_pos, right, y_pos)
            y_pos += minor_step
            y_idx += 1

        _apply_rule_stroke(pdf, device=device, theme=theme)
        x_pos = left + minor_step
        x_idx = 1
        while x_pos < right:
            if x_idx % major_every == 0:
                pdf.line(x_pos, bottom, x_pos, header_bottom)
            x_pos += minor_step
            x_idx += 1

        y_pos = bottom + minor_step
        y_idx = 1
        while y_pos < header_bottom:
            if y_idx % major_every == 0:
                pdf.line(left, y_pos, right, y_pos)
            y_pos += minor_step
            y_idx += 1
        return

    msg = f"unknown notes fill '{notes_fill}'. Valid notes fills: {', '.join(NOTES_FILL_TYPES)}."
    raise ValueError(msg)


def _draw_todo_list_template(
    pdf: DrawingPrimitives,
    *,
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
    theme: type = Theme,
) -> None:
    _draw_checklist_template(pdf, device=device, layout=layout, title="TO DO LIST", theme=theme)


TEMPLATE_RENDERERS = {
    "lines": _draw_lines_template,
    "grid": _draw_grid_template,
    "dotted-grid": _draw_dotted_grid_template,
    "day-at-glance": _draw_day_at_glance_template,
    "schedule": _draw_schedule_template,
    "task-list": _draw_task_list_template,
    "notes": _draw_notes_template,
    "todo-list": _draw_todo_list_template,
}
