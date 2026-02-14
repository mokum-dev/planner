"""Theme profile schema and resolver."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from reportlab.lib import colors


@dataclass(frozen=True)
class ThemeProfile:
    """Serializable theme profile values."""

    background: str = "#F9F9F9"
    sidebar_bg: str = "#2C3E50"
    sidebar_text: str = "#FFFFFF"
    text_primary: str = "#2C3E50"
    text_secondary: str = "#7F8C8D"
    accent: str = "#E67E22"
    grid_lines: str = "#BDC3C7"
    writing_lines: str = "#EEEEEE"
    link_badge_bg: str = "#F2F2F2"
    font_header: str = "Helvetica-Bold"
    font_regular: str = "Helvetica"
    font_bold: str = "Helvetica-Bold"

    def to_theme_class(self) -> type:
        """Return a runtime Theme-like class with parsed color objects."""
        return type(
            "Theme",
            (),
            {
                "BACKGROUND": _parse_color(self.background, key="background"),
                "SIDEBAR_BG": _parse_color(self.sidebar_bg, key="sidebar_bg"),
                "SIDEBAR_TEXT": _parse_color(self.sidebar_text, key="sidebar_text"),
                "TEXT_PRIMARY": _parse_color(self.text_primary, key="text_primary"),
                "TEXT_SECONDARY": _parse_color(self.text_secondary, key="text_secondary"),
                "ACCENT": _parse_color(self.accent, key="accent"),
                "GRID_LINES": _parse_color(self.grid_lines, key="grid_lines"),
                "WRITING_LINES": _parse_color(self.writing_lines, key="writing_lines"),
                "LINK_BADGE_BG": _parse_color(self.link_badge_bg, key="link_badge_bg"),
                "FONT_HEADER": _parse_font(self.font_header, key="font_header"),
                "FONT_REGULAR": _parse_font(self.font_regular, key="font_regular"),
                "FONT_BOLD": _parse_font(self.font_bold, key="font_bold"),
            },
        )


_BUILTIN_THEME_PROFILES: dict[str, ThemeProfile] = {
    "default": ThemeProfile(),
}


def available_theme_profiles() -> tuple[str, ...]:
    """Return built-in theme profile names."""
    return tuple(sorted(_BUILTIN_THEME_PROFILES))


def resolve_theme(
    *,
    profile: str = "default",
    theme_file: str | Path | None = None,
) -> type:
    """Resolve one built-in theme plus optional file overrides."""
    if profile not in _BUILTIN_THEME_PROFILES:
        valid = ", ".join(available_theme_profiles())
        msg = f"unknown theme profile '{profile}'. Valid profiles: {valid}."
        raise ValueError(msg)

    resolved_profile = _BUILTIN_THEME_PROFILES[profile]
    if theme_file is not None:
        resolved_profile = replace(resolved_profile, **_load_theme_file(Path(theme_file)))
    return resolved_profile.to_theme_class()


def _load_theme_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        msg = f"theme file '{path}' does not exist."
        raise ValueError(msg)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"theme file '{path}' is not valid JSON: {exc}."
        raise ValueError(msg) from exc

    if not isinstance(payload, dict):
        msg = "theme file content must be a JSON object."
        raise ValueError(msg)

    allowed = set(ThemeProfile.__dataclass_fields__)
    unknown = sorted(key for key in payload if key not in allowed)
    if unknown:
        msg = f"unknown theme key(s): {', '.join(unknown)}."
        raise ValueError(msg)

    return payload


def _parse_color(raw_value: str, *, key: str) -> colors.Color:
    if not isinstance(raw_value, str) or not raw_value.strip():
        msg = f"theme key '{key}' must be a non-empty color string."
        raise ValueError(msg)
    try:
        if raw_value.startswith("#"):
            return colors.HexColor(raw_value)
        return colors.toColor(raw_value)
    except Exception as exc:  # noqa: BLE001
        msg = f"invalid color value '{raw_value}' for theme key '{key}'."
        raise ValueError(msg) from exc


def _parse_font(raw_value: str, *, key: str) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        msg = f"theme key '{key}' must be a non-empty font name string."
        raise ValueError(msg)
    return raw_value
