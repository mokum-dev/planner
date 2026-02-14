"""Template generation facade and public API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import sys

from .config import DEFAULT_TEMPLATE_FILENAME_TEMPLATE, Theme
from .drawing import create_reportlab_primitives
from .profiles import DEFAULT_DEVICE, DEVICE_PROFILES
from .rendering import render_page_block
from .template_engine import resolve_template_params
from .template_layout import (
    TEMPLATE_LAYOUT_PROFILES,
    TemplateLayoutProfile,
    font_pt_to_device_units,
    mm_to_device_units,
    pt_to_device_units,
    resolve_template_layout,
)
from .template_renderers import NOTES_FILL_TYPES, TEMPLATE_RENDERERS
from .template_specs import (
    TEMPLATE_TYPES,
    available_template_types,
    build_template_registry,
    get_template_spec,
    list_template_specs,
)

SCHEDULE_TEMPLATE_DEFAULT_START_HOUR = 6
SCHEDULE_TEMPLATE_DEFAULT_END_HOUR = 22

_LAYOUT_OVERRIDE_KEYS = (
    "margin_mm",
    "header_height_mm",
    "line_spacing_mm",
    "grid_spacing_mm",
    "dot_spacing_mm",
    "dot_radius_mm",
    "checklist_rows",
    "priorities_rows",
    "schedule_start_hour",
    "schedule_end_hour",
)


def generate_template(
    template: str,
    output_path: str | Path | None = None,
    *,
    device: str = DEFAULT_DEVICE,
    layout: str | None = None,
    param_overrides: Mapping[str, object] | None = None,
    plugin_modules: Sequence[str] = (),
    theme: type = Theme,
) -> Path:
    """Generate a single-page template PDF and return the output path."""
    if device not in DEVICE_PROFILES:
        msg = f"unknown device '{device}'. Valid devices: {', '.join(sorted(DEVICE_PROFILES))}."
        raise ValueError(msg)

    registry, warnings = build_template_registry(plugin_modules=plugin_modules)
    for warning in warnings:
        print(warning, file=sys.stderr)

    template_spec = registry.get(template)
    resolved_params = resolve_template_params(
        spec=template_spec,
        raw_params=param_overrides,
    )

    effective_schedule_start = resolved_params.get("schedule_start_hour")
    effective_schedule_end = resolved_params.get("schedule_end_hour")
    if template_spec.template_id == "schedule":
        if effective_schedule_start is None:
            effective_schedule_start = SCHEDULE_TEMPLATE_DEFAULT_START_HOUR
        if effective_schedule_end is None:
            effective_schedule_end = SCHEDULE_TEMPLATE_DEFAULT_END_HOUR
    resolved_params["schedule_start_hour"] = effective_schedule_start
    resolved_params["schedule_end_hour"] = effective_schedule_end

    layout_overrides = {key: resolved_params.get(key) for key in _LAYOUT_OVERRIDE_KEYS}
    template_layout = resolve_template_layout(
        device=device,
        layout=layout,
        margin_mm=layout_overrides["margin_mm"],
        header_height_mm=layout_overrides["header_height_mm"],
        line_spacing_mm=layout_overrides["line_spacing_mm"],
        grid_spacing_mm=layout_overrides["grid_spacing_mm"],
        dot_spacing_mm=layout_overrides["dot_spacing_mm"],
        dot_radius_mm=layout_overrides["dot_radius_mm"],
        checklist_rows=layout_overrides["checklist_rows"],
        priorities_rows=layout_overrides["priorities_rows"],
        schedule_start_hour=layout_overrides["schedule_start_hour"],
        schedule_end_hour=layout_overrides["schedule_end_hour"],
    )

    device_profile = DEVICE_PROFILES[device]
    destination = Path(
        output_path
        or DEFAULT_TEMPLATE_FILENAME_TEMPLATE.format(
            template=template_spec.template_id.replace("-", "_"),
            device=device,
        )
    )
    destination.parent.mkdir(parents=True, exist_ok=True)

    pdf = create_reportlab_primitives(
        str(destination),
        pagesize=(device_profile.page_width, device_profile.page_height),
    )
    pdf.set_title(f"{template_spec.title} Template ({device_profile.name}, {template_layout.name})")

    root_block = template_spec.build(resolved_params)
    render_page_block(
        pdf,
        block=root_block,
        device_profile=device_profile,
        layout_profile=template_layout,
        theme=theme,
    )
    pdf.save()
    return destination


__all__ = [
    "TEMPLATE_LAYOUT_PROFILES",
    "TEMPLATE_TYPES",
    "TemplateLayoutProfile",
    "NOTES_FILL_TYPES",
    "TEMPLATE_RENDERERS",
    "available_template_types",
    "build_template_registry",
    "font_pt_to_device_units",
    "generate_template",
    "get_template_spec",
    "list_template_specs",
    "mm_to_device_units",
    "pt_to_device_units",
    "resolve_template_layout",
]
