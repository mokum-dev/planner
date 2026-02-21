"""Shared page rendering helpers for block-driven pipelines."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import Theme
from .drawing import DrawingPrimitives
from .profiles import DeviceProfile
from .template_engine import Block, Rect, RenderContext


def _mm_to_units(value_mm: float, *, device_profile: DeviceProfile) -> float:
    return (value_mm / 25.4) * device_profile.pixels_per_inch


def _pt_to_units(value_pt: float, *, device_profile: DeviceProfile) -> float:
    return value_pt * (device_profile.pixels_per_inch / 72.0)


def _font_pt_to_units(value_pt: float, *, device_profile: DeviceProfile) -> float:
    return _pt_to_units(
        value_pt * device_profile.template_font_scale, device_profile=device_profile
    )


def render_page_block(
    pdf: DrawingPrimitives,
    *,
    block: Block,
    device_profile: DeviceProfile,
    layout_profile: object,
    theme: type = Theme,
    extras: Mapping[str, Any] | None = None,
) -> None:
    """Render one block-based page and advance the PDF cursor."""
    context = RenderContext(
        pdf=pdf,
        device_profile=device_profile,
        layout_profile=layout_profile,
        theme=theme,
        mm_to_units=lambda value_mm: _mm_to_units(value_mm, device_profile=device_profile),
        pt_to_units=lambda value_pt: _pt_to_units(value_pt, device_profile=device_profile),
        font_pt_to_units=lambda value_pt: _font_pt_to_units(
            value_pt, device_profile=device_profile
        ),
        extras=dict(extras or {}),
    )
    page_rect = Rect(
        left=0,
        bottom=0,
        right=device_profile.page_width,
        top=device_profile.page_height,
    )
    block.render(context, page_rect)
    pdf.show_page()
