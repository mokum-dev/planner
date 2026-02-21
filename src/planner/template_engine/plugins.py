"""Plugin loading for external template specs."""

from __future__ import annotations

import importlib
import importlib.metadata
from collections.abc import Callable, Iterable
from types import ModuleType
from typing import Any

from .registry import TemplateRegistry

PLUGIN_API_VERSION = 1


def _entry_points_for_group(group: str) -> list[importlib.metadata.EntryPoint]:
    entry_points = importlib.metadata.entry_points()
    if hasattr(entry_points, "select"):
        return list(entry_points.select(group=group))
    selected = entry_points.get(group, ())  # pragma: no cover - legacy fallback
    return list(selected)


def _resolve_register_fn(loaded_obj: Any) -> Callable[[TemplateRegistry], None]:
    if isinstance(loaded_obj, ModuleType):
        register_fn = getattr(loaded_obj, "register_templates", None)
        if not callable(register_fn):
            msg = f"module '{loaded_obj.__name__}' does not define register_templates(registry)."
            raise ValueError(msg)

        plugin_version = getattr(loaded_obj, "PLUGIN_API_VERSION", PLUGIN_API_VERSION)
        if plugin_version != PLUGIN_API_VERSION:
            msg = (
                f"module '{loaded_obj.__name__}' targets plugin API version {plugin_version}, "
                f"expected {PLUGIN_API_VERSION}."
            )
            raise ValueError(msg)
        return register_fn

    if callable(loaded_obj):
        return loaded_obj

    msg = "plugin entry point must resolve to a module or callable."
    raise ValueError(msg)


def _load_one(registry: TemplateRegistry, loader: Callable[[], Any], *, source: str) -> str | None:
    try:
        loaded = loader()
        register_fn = _resolve_register_fn(loaded)
        register_fn(registry)
    except Exception as exc:  # noqa: BLE001
        return f"warning: failed to load template plugin '{source}': {exc}"
    return None


def load_template_plugins(
    *,
    registry: TemplateRegistry,
    module_paths: Iterable[str] = (),
    entry_point_group: str = "planner.templates",
) -> tuple[str, ...]:
    """Load plugin modules and entry points, collecting warning strings."""
    warnings: list[str] = []

    for module_path in module_paths:
        warning = _load_one(
            registry,
            lambda module_path=module_path: importlib.import_module(module_path),
            source=module_path,
        )
        if warning:
            warnings.append(warning)

    for entry_point in _entry_points_for_group(entry_point_group):
        warning = _load_one(
            registry,
            entry_point.load,
            source=f"{entry_point.name} ({entry_point.value})",
        )
        if warning:
            warnings.append(warning)

    return tuple(warnings)
