"""Built-in template metadata/spec definitions and registry helpers."""

from __future__ import annotations

from collections.abc import Sequence

from .template_blocks import CallbackBlock
from .template_engine import (
    Rect,
    RenderContext,
    TemplateParamSpec,
    TemplateRegistry,
    TemplateSpec,
    load_template_plugins,
)
from .template_renderers import NOTES_FILL_TYPES, TEMPLATE_RENDERERS, draw_page_background

BUILTIN_TEMPLATE_METADATA = (
    ("lines", "Lines", "Ruled writing lines."),
    ("grid", "Grid", "Square graph grid."),
    ("dotted-grid", "Dotted Grid", "Dot-matrix writing grid."),
    ("day-at-glance", "Day At A Glance", "Daily dashboard with schedule and priorities."),
    ("schedule", "Schedule", "Hour-by-hour schedule template."),
    ("task-list", "Task List", "Checklist-oriented task list."),
    ("notes", "Notes", "Flexible notes page with configurable fill."),
    ("todo-list", "To Do List", "Checklist alias for compatibility."),
)

TEMPLATE_TYPES = tuple(template_id for template_id, _, _ in BUILTIN_TEMPLATE_METADATA)

_COMMON_PARAM_SPECS = (
    TemplateParamSpec(
        key="margin_mm",
        value_type=float,
        description="Page margin in millimeters.",
        min_value=0.000001,
    ),
    TemplateParamSpec(
        key="header_height_mm",
        value_type=float,
        description="Header band height in millimeters.",
        min_value=0.0,
    ),
    TemplateParamSpec(
        key="line_spacing_mm",
        value_type=float,
        description="Writing line spacing in millimeters.",
        min_value=0.000001,
    ),
    TemplateParamSpec(
        key="grid_spacing_mm",
        value_type=float,
        description="Grid spacing in millimeters.",
        min_value=0.000001,
    ),
    TemplateParamSpec(
        key="dot_spacing_mm",
        value_type=float,
        description="Dot spacing in millimeters.",
        min_value=0.000001,
    ),
    TemplateParamSpec(
        key="dot_radius_mm",
        value_type=float,
        description="Dot radius in millimeters.",
        min_value=0.000001,
    ),
    TemplateParamSpec(
        key="checklist_rows",
        value_type=int,
        description="Checklist row count.",
        min_value=1.0,
    ),
    TemplateParamSpec(
        key="priorities_rows",
        value_type=int,
        description="Priority row count for daily glance.",
        min_value=1.0,
    ),
    TemplateParamSpec(
        key="schedule_start_hour",
        value_type=int,
        description="Schedule start hour in 24h format.",
        min_value=0.0,
        max_value=23.0,
    ),
    TemplateParamSpec(
        key="schedule_end_hour",
        value_type=int,
        description="Schedule end hour in 24h format.",
        min_value=1.0,
        max_value=24.0,
    ),
    TemplateParamSpec(
        key="notes_fill",
        value_type=str,
        description="Notes fill type.",
        default="lines",
        choices=NOTES_FILL_TYPES,
    ),
)


def _build_standard_template_spec(template_id: str, title: str, description: str) -> TemplateSpec:
    def build(params: dict[str, object]) -> CallbackBlock:
        _ = params

        def render_standard(ctx: RenderContext, rect: Rect) -> None:
            _ = rect
            draw_page_background(ctx.pdf, ctx.device_profile, theme=ctx.theme)
            renderer = TEMPLATE_RENDERERS[template_id]
            renderer(
                ctx.pdf,
                device=ctx.device_profile,
                layout=ctx.layout_profile,
                theme=ctx.theme,
            )

        return CallbackBlock(callback=render_standard)

    return TemplateSpec(
        template_id=template_id,
        title=title,
        description=description,
        build=build,
        params=_COMMON_PARAM_SPECS,
    )


def _build_notes_template_spec() -> TemplateSpec:
    def build(params: dict[str, object]) -> CallbackBlock:
        notes_fill = str(params.get("notes_fill", "lines"))

        def render_notes(ctx: RenderContext, rect: Rect) -> None:
            _ = rect
            draw_page_background(ctx.pdf, ctx.device_profile, theme=ctx.theme)
            notes_renderer = TEMPLATE_RENDERERS["notes"]
            notes_renderer(
                ctx.pdf,
                device=ctx.device_profile,
                layout=ctx.layout_profile,
                notes_fill=notes_fill,
                theme=ctx.theme,
            )

        return CallbackBlock(callback=render_notes)

    return TemplateSpec(
        template_id="notes",
        title="Notes",
        description="Flexible notes page with configurable fill.",
        build=build,
        params=_COMMON_PARAM_SPECS,
    )


def _builtin_template_specs() -> tuple[TemplateSpec, ...]:
    specs: list[TemplateSpec] = []
    for template_id, title, description in BUILTIN_TEMPLATE_METADATA:
        if template_id == "notes":
            specs.append(_build_notes_template_spec())
            continue
        specs.append(_build_standard_template_spec(template_id, title, description))
    return tuple(specs)


def build_template_registry(
    *,
    plugin_modules: Sequence[str] = (),
) -> tuple[TemplateRegistry, tuple[str, ...]]:
    """Return a registry with built-ins and optional plugin templates."""
    registry = TemplateRegistry()
    registry.register_many(_builtin_template_specs())
    warnings = load_template_plugins(registry=registry, module_paths=plugin_modules)
    return registry, warnings


def available_template_types(*, plugin_modules: Sequence[str] = ()) -> tuple[str, ...]:
    """Return template ids currently available to the generator."""
    registry, _ = build_template_registry(plugin_modules=plugin_modules)
    return tuple(spec.template_id for spec in registry.list_specs())


def list_template_specs(*, plugin_modules: Sequence[str] = ()) -> tuple[TemplateSpec, ...]:
    """Return all registered template specs."""
    registry, _ = build_template_registry(plugin_modules=plugin_modules)
    return registry.list_specs()


def get_template_spec(template: str, *, plugin_modules: Sequence[str] = ()) -> TemplateSpec:
    """Return one resolved template spec by id or alias."""
    registry, _ = build_template_registry(plugin_modules=plugin_modules)
    return registry.get(template)
