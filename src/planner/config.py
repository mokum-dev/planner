"""Configuration constants for planner rendering."""

from reportlab.lib import colors

# 1404 x 1872 is a high-resolution 3:4 aspect ratio.
PAGE_WIDTH = 1404
PAGE_HEIGHT = 1872

# Layout
SIDEBAR_WIDTH = 140
MARGIN = 50
HEADER_HEIGHT = 160

# File output
DEFAULT_FILENAME_TEMPLATE = "planner_{year}.pdf"
DEFAULT_TEMPLATE_FILENAME_TEMPLATE = "template_{template}_{device}.pdf"

# Sidebar month labels
MONTH_LABELS = (
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


class Theme:
    """Color and font choices for rendering."""

    BACKGROUND = colors.HexColor("#F9F9F9")
    SIDEBAR_BG = colors.HexColor("#2C3E50")
    SIDEBAR_TEXT = colors.white

    TEXT_PRIMARY = colors.HexColor("#2C3E50")
    TEXT_SECONDARY = colors.HexColor("#7F8C8D")

    ACCENT = colors.HexColor("#E67E22")
    GRID_LINES = colors.HexColor("#BDC3C7")
    WRITING_LINES = colors.HexColor("#EEEEEE")
    LINK_BADGE_BG = colors.HexColor("#F2F2F2")

    FONT_HEADER = "Helvetica-Bold"
    FONT_REGULAR = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"
