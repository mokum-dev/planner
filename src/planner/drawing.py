"""Drawing primitives and backend adapters."""

from __future__ import annotations

from typing import Any, Protocol

from reportlab.pdfgen import canvas


class DrawingPrimitives(Protocol):
    """Backend-agnostic drawing primitives used by renderers."""

    def set_fill_color(self, color: Any) -> None: ...
    def set_stroke_color(self, color: Any) -> None: ...
    def set_line_width(self, width: float) -> None: ...
    def set_font(self, font_name: str, size: float) -> None: ...
    def string_width(self, text: str, font_name: str, size: float) -> float: ...
    def draw_string(self, x: float, y: float, text: str) -> None: ...
    def draw_centred_string(self, x: float, y: float, text: str) -> None: ...
    def draw_right_string(self, x: float, y: float, text: str) -> None: ...
    def line(self, x1: float, y1: float, x2: float, y2: float) -> None: ...
    def rect(
        self, x: float, y: float, width: float, height: float, *, fill: int = 0, stroke: int = 1
    ) -> None: ...
    def round_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float,
        *,
        fill: int = 0,
        stroke: int = 1,
    ) -> None: ...
    def circle(
        self, x: float, y: float, radius: float, *, fill: int = 0, stroke: int = 1
    ) -> None: ...
    def link_rect(self, destination: str, rect: tuple[float, float, float, float]) -> None: ...
    def bookmark_page(self, key: str) -> None: ...
    def add_outline_entry(self, title: str, key: str, *, level: int) -> None: ...
    def save_state(self) -> None: ...
    def restore_state(self) -> None: ...
    def translate(self, x: float, y: float) -> None: ...
    def rotate(self, angle: float) -> None: ...
    def set_title(self, title: str) -> None: ...
    def show_page(self) -> None: ...
    def save(self) -> None: ...


class ReportLabPrimitives:
    """ReportLab-backed implementation of DrawingPrimitives."""

    def __init__(self, target: canvas.Canvas) -> None:
        self._target = target

    def set_fill_color(self, color: Any) -> None:
        self._target.setFillColor(color)

    def set_stroke_color(self, color: Any) -> None:
        self._target.setStrokeColor(color)

    def set_line_width(self, width: float) -> None:
        self._target.setLineWidth(width)

    def set_font(self, font_name: str, size: float) -> None:
        self._target.setFont(font_name, size)

    def string_width(self, text: str, font_name: str, size: float) -> float:
        return self._target.stringWidth(text, font_name, size)

    def draw_string(self, x: float, y: float, text: str) -> None:
        self._target.drawString(x, y, text)

    def draw_centred_string(self, x: float, y: float, text: str) -> None:
        self._target.drawCentredString(x, y, text)

    def draw_right_string(self, x: float, y: float, text: str) -> None:
        self._target.drawRightString(x, y, text)

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self._target.line(x1, y1, x2, y2)

    def rect(
        self, x: float, y: float, width: float, height: float, *, fill: int = 0, stroke: int = 1
    ) -> None:
        self._target.rect(x, y, width, height, fill=fill, stroke=stroke)

    def round_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float,
        *,
        fill: int = 0,
        stroke: int = 1,
    ) -> None:
        self._target.roundRect(x, y, width, height, radius, fill=fill, stroke=stroke)

    def circle(self, x: float, y: float, radius: float, *, fill: int = 0, stroke: int = 1) -> None:
        self._target.circle(x, y, radius, fill=fill, stroke=stroke)

    def link_rect(self, destination: str, rect: tuple[float, float, float, float]) -> None:
        self._target.linkRect("", destination, rect, thickness=0)

    def bookmark_page(self, key: str) -> None:
        self._target.bookmarkPage(key)

    def add_outline_entry(self, title: str, key: str, *, level: int) -> None:
        self._target.addOutlineEntry(title, key, level=level)

    def save_state(self) -> None:
        self._target.saveState()

    def restore_state(self) -> None:
        self._target.restoreState()

    def translate(self, x: float, y: float) -> None:
        self._target.translate(x, y)

    def rotate(self, angle: float) -> None:
        self._target.rotate(angle)

    def set_title(self, title: str) -> None:
        self._target.setTitle(title)

    def show_page(self) -> None:
        self._target.showPage()

    def save(self) -> None:
        self._target.save()


def create_reportlab_primitives(
    output_path: str,
    *,
    pagesize: tuple[float, float],
) -> ReportLabPrimitives:
    """Create a ReportLab-backed primitives renderer."""
    return ReportLabPrimitives(canvas.Canvas(output_path, pagesize=pagesize))
