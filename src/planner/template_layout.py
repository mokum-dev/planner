"""Template layout profiles and unit conversion helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .profiles import DEFAULT_DEVICE, DEVICE_PROFILES, DeviceProfile


@dataclass(frozen=True)
class TemplateLayoutProfile:
    """Logical layout parameters shared across template types."""

    name: str
    margin_mm: float = 10.0
    header_height_mm: float = 10.0
    line_spacing_mm: float = 7.0
    grid_spacing_mm: float = 5.0
    dot_spacing_mm: float = 5.0
    dot_radius_mm: float = 0.35
    checklist_rows: int = 18
    priorities_rows: int = 6
    schedule_start_hour: int = 6
    schedule_end_hour: int = 22


TEMPLATE_LAYOUT_PROFILES = {
    "full": TemplateLayoutProfile(
        name="full",
        margin_mm=12.0,
        header_height_mm=12.0,
        line_spacing_mm=8.0,
        grid_spacing_mm=6.0,
        dot_spacing_mm=6.0,
        dot_radius_mm=0.38,
        checklist_rows=16,
        priorities_rows=5,
        schedule_start_hour=6,
        schedule_end_hour=22,
    ),
    "balanced": TemplateLayoutProfile(
        name="balanced",
        margin_mm=10.0,
        header_height_mm=10.0,
        line_spacing_mm=7.0,
        grid_spacing_mm=5.0,
        dot_spacing_mm=5.0,
        dot_radius_mm=0.35,
        checklist_rows=18,
        priorities_rows=6,
        schedule_start_hour=6,
        schedule_end_hour=22,
    ),
    "compact": TemplateLayoutProfile(
        name="compact",
        margin_mm=8.0,
        header_height_mm=8.0,
        line_spacing_mm=6.0,
        grid_spacing_mm=4.5,
        dot_spacing_mm=4.5,
        dot_radius_mm=0.3,
        checklist_rows=22,
        priorities_rows=8,
        schedule_start_hour=7,
        schedule_end_hour=22,
    ),
}


DEFAULT_TEMPLATE_LAYOUT_BY_DEVICE = {
    "remarkable": "balanced",
    "scribe": "full",
    "palma": "compact",
}


DEFAULT_TEMPLATE_LAYOUT_OVERRIDES_BY_DEVICE = {
    "palma": {
        "margin_mm": 3.0,
        "schedule_start_hour": 9,
        "schedule_end_hour": 19,
    },
}


def mm_to_device_units(value_mm: float, *, device: DeviceProfile) -> float:
    """Convert physical millimeters into device canvas units."""
    if device.pixels_per_inch <= 0:
        msg = "device pixels_per_inch must be positive."
        raise ValueError(msg)
    return (value_mm / 25.4) * device.pixels_per_inch


def pt_to_device_units(value_pt: float, *, device: DeviceProfile) -> float:
    """Convert typographic points into device canvas units."""
    if device.pixels_per_inch <= 0:
        msg = "device pixels_per_inch must be positive."
        raise ValueError(msg)
    return value_pt * (device.pixels_per_inch / 72.0)


def font_pt_to_device_units(value_pt: float, *, device: DeviceProfile) -> float:
    """Convert points into device units with device-specific template text scaling."""
    return pt_to_device_units(value_pt * device.template_font_scale, device=device)


def _validate_template_layout(layout: TemplateLayoutProfile) -> None:
    if layout.margin_mm <= 0:
        msg = "template margin must be positive."
        raise ValueError(msg)
    if layout.header_height_mm < 0:
        msg = "template header height must be >= 0."
        raise ValueError(msg)
    if layout.line_spacing_mm <= 0:
        msg = "template line spacing must be positive."
        raise ValueError(msg)
    if layout.grid_spacing_mm <= 0:
        msg = "template grid spacing must be positive."
        raise ValueError(msg)
    if layout.dot_spacing_mm <= 0:
        msg = "template dot spacing must be positive."
        raise ValueError(msg)
    if layout.dot_radius_mm <= 0:
        msg = "template dot radius must be positive."
        raise ValueError(msg)
    if layout.checklist_rows < 1:
        msg = "template checklist rows must be >= 1."
        raise ValueError(msg)
    if layout.priorities_rows < 1:
        msg = "template priorities rows must be >= 1."
        raise ValueError(msg)
    if not 0 <= layout.schedule_start_hour <= 23:
        msg = "template schedule start hour must be between 0 and 23."
        raise ValueError(msg)
    if not 1 <= layout.schedule_end_hour <= 24:
        msg = "template schedule end hour must be between 1 and 24."
        raise ValueError(msg)
    if layout.schedule_end_hour <= layout.schedule_start_hour:
        msg = "template schedule end hour must be greater than start hour."
        raise ValueError(msg)


def resolve_template_layout(
    *,
    device: str = DEFAULT_DEVICE,
    layout: str | None = None,
    margin_mm: float | None = None,
    header_height_mm: float | None = None,
    line_spacing_mm: float | None = None,
    grid_spacing_mm: float | None = None,
    dot_spacing_mm: float | None = None,
    dot_radius_mm: float | None = None,
    checklist_rows: int | None = None,
    priorities_rows: int | None = None,
    schedule_start_hour: int | None = None,
    schedule_end_hour: int | None = None,
) -> TemplateLayoutProfile:
    """Resolve a template layout profile and apply optional parameter overrides."""
    if device not in DEVICE_PROFILES:
        msg = f"unknown device '{device}'. Valid devices: {', '.join(sorted(DEVICE_PROFILES))}."
        raise ValueError(msg)

    layout_name = layout or DEFAULT_TEMPLATE_LAYOUT_BY_DEVICE[device]
    if layout_name not in TEMPLATE_LAYOUT_PROFILES:
        msg = (
            f"unknown template layout '{layout_name}'. Valid template layouts: "
            f"{', '.join(sorted(TEMPLATE_LAYOUT_PROFILES))}."
        )
        raise ValueError(msg)

    device_defaults = DEFAULT_TEMPLATE_LAYOUT_OVERRIDES_BY_DEVICE.get(device, {})
    overrides = {
        key: value
        for key, value in {
            "margin_mm": margin_mm,
            "header_height_mm": header_height_mm,
            "line_spacing_mm": line_spacing_mm,
            "grid_spacing_mm": grid_spacing_mm,
            "dot_spacing_mm": dot_spacing_mm,
            "dot_radius_mm": dot_radius_mm,
            "checklist_rows": checklist_rows,
            "priorities_rows": priorities_rows,
            "schedule_start_hour": schedule_start_hour,
            "schedule_end_hour": schedule_end_hour,
        }.items()
        if value is not None
    }
    selected = replace(TEMPLATE_LAYOUT_PROFILES[layout_name], **device_defaults)
    selected = replace(selected, **overrides)
    _validate_template_layout(selected)
    return selected


def content_bounds(
    device: DeviceProfile,
    layout: TemplateLayoutProfile,
) -> tuple[float, float, float, float]:
    """Return drawable content bounds for the chosen device/layout."""
    margin = mm_to_device_units(layout.margin_mm, device=device)
    left = margin
    right = device.page_width - margin
    bottom = margin
    top = device.page_height - margin

    if right <= left or top <= bottom:
        msg = "template margins leave no drawable area."
        raise ValueError(msg)
    return (left, bottom, right, top)
