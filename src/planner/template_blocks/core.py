"""Composable block primitives."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from planner.template_engine import Block, Rect, RenderContext


@dataclass(frozen=True)
class CompositeBlock:
    """Render multiple blocks in order."""

    blocks: Sequence[Block]

    def render(self, ctx: RenderContext, rect: Rect) -> None:
        for block in self.blocks:
            block.render(ctx, rect)


@dataclass(frozen=True)
class CallbackBlock:
    """Wrap a callback as a block."""

    callback: Callable[[RenderContext, Rect], None]

    def render(self, ctx: RenderContext, rect: Rect) -> None:
        self.callback(ctx, rect)


@dataclass(frozen=True)
class InsetBlock:
    """Inset the target rect before rendering the inner block."""

    block: Block
    left: float = 0.0
    right: float = 0.0
    top: float = 0.0
    bottom: float = 0.0

    def render(self, ctx: RenderContext, rect: Rect) -> None:
        self.block.render(
            ctx,
            rect.inset(left=self.left, right=self.right, top=self.top, bottom=self.bottom),
        )


@dataclass(frozen=True)
class PageBackgroundBlock:
    """Fill the whole page with one color."""

    color: Any

    def render(self, ctx: RenderContext, rect: Rect) -> None:  # noqa: ARG002 - full-page fill by design
        ctx.pdf.set_fill_color(self.color)
        ctx.pdf.rect(0, 0, ctx.device_profile.page_width, ctx.device_profile.page_height, fill=1, stroke=0)
