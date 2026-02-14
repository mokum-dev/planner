"""Core contracts for template composition and registration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from planner.drawing import DrawingPrimitives
from planner.profiles import DeviceProfile

MISSING = object()


@dataclass(frozen=True)
class Rect:
    """Simple rectangle bounds in device units."""

    left: float
    bottom: float
    right: float
    top: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    def inset(
        self,
        *,
        left: float = 0.0,
        right: float = 0.0,
        top: float = 0.0,
        bottom: float = 0.0,
    ) -> Rect:
        """Return a rect inset by each edge offset."""
        return Rect(
            left=self.left + left,
            bottom=self.bottom + bottom,
            right=self.right - right,
            top=self.top - top,
        )


@dataclass(frozen=True)
class RenderContext:
    """Context shared by all blocks during rendering."""

    pdf: DrawingPrimitives
    device_profile: DeviceProfile
    layout_profile: object
    theme: type
    mm_to_units: Callable[[float], float]
    pt_to_units: Callable[[float], float]
    font_pt_to_units: Callable[[float], float]
    extras: dict[str, Any] = field(default_factory=dict)


class Block(Protocol):
    """Composable rendering unit."""

    def render(self, ctx: RenderContext, rect: Rect) -> None:
        """Draw into the target rectangle."""


@dataclass(frozen=True)
class TemplateParamSpec:
    """Validation rules for one template parameter."""

    key: str
    value_type: type
    description: str
    required: bool = False
    default: Any = MISSING
    choices: tuple[Any, ...] = ()
    min_value: float | None = None
    max_value: float | None = None
    aliases: tuple[str, ...] = ()

    def all_keys(self) -> tuple[str, ...]:
        return (self.key, *self.aliases)

    @property
    def has_default(self) -> bool:
        return self.default is not MISSING


@dataclass(frozen=True)
class TemplateSpec:
    """Registry metadata and builder callback for a template."""

    template_id: str
    title: str
    description: str
    build: Callable[[dict[str, Any]], Block]
    params: tuple[TemplateParamSpec, ...] = ()
    aliases: tuple[str, ...] = ()
    supported_devices: tuple[str, ...] = ()
