# Planner

Generate either:
- a full-year planner PDF (cover + monthly + weekly + daily pages), or
- a single-page note template PDF (for handwritten background pages),
using ReportLab.

## Requirements

- Python 3.14+
- `uv` for dependency management and command execution

## Quick Start

```bash
uv sync
uv run planner --year 2026 --output planner_2026.pdf
```

Template quick start:

```bash
uv run planner templates generate lines --output template_lines.pdf
```

## Device And Layout Profiles

The generator supports built-in device/page targets and layout densities:

- Devices: `remarkable`, `scribe`, `palma`
- Layouts: `full`, `balanced`, `compact`

Compact layout behavior:

- Weekly pages are split into two segments (`MON-THU`, `FRI-SUN`) when needed.
- Daily pages switch to a full-width notes grid (no schedule/priorities columns).

Auto-fit behavior:

- The generator validates minimum cell/tap sizes for the chosen device/layout.
- If the requested layout does not fit, it automatically falls back to denser layouts.
- Use `--strict-layout` to disable fallback and fail instead.

Examples:

```bash
# Device default layout (reMarkable -> full)
uv run planner --year 2026 --device remarkable --output planner_rm2.pdf

# Small-screen target with compact layout
uv run planner --year 2026 --device palma --layout compact --output planner_palma.pdf

# Request a non-fitting layout and force an error instead of fallback
uv run planner --year 2026 --device palma --layout full --strict-layout
```

## Template Generator

Template mode renders a single-page PDF with no calendar navigation and supports the same device targets:

- Devices: `remarkable`, `scribe`, `palma`
- Templates: `lines`, `grid`, `dotted-grid`, `day-at-glance`, `schedule`, `task-list`, `notes`, `todo-list` (`todo-list` remains supported for compatibility)
- Template layouts: `full`, `balanced`, `compact`

Examples:

```bash
# Dotted grid tuned for BOOX Palma
uv run planner templates generate dotted-grid --device palma --layout compact --output palma_dots.pdf

# Day-at-glance with custom layout parameters
uv run planner templates generate day-at-glance \
  --param margin_mm=9 --param line_spacing_mm=6.5 --param priorities_rows=7 \
  --param schedule_start_hour=7 --param schedule_end_hour=23 \
  --output day_glance_custom.pdf

# Standalone Palma schedule/task/notes pages
uv run planner templates generate schedule --device palma --output palma_schedule.pdf
uv run planner templates generate task-list --device palma --output palma_tasks.pdf
uv run planner templates generate notes --device palma --output palma_notes.pdf

# Notes template with graph-paper style (1mm minor / 5mm major)
uv run planner templates generate notes --param notes_fill=millimeter --output notes_graph.pdf

# Discover available template specs and parameters
uv run planner templates list
uv run planner templates show notes

# Generic per-template override channel (repeatable)
uv run planner templates generate notes --param notes_fill=grid --output notes_grid.pdf
```

Supported template parameter keys for `--param key=value`:

- `margin_mm`
- `header_height_mm`
- `line_spacing_mm`
- `grid_spacing_mm`
- `dot_spacing_mm`
- `dot_radius_mm`
- `checklist_rows`
- `priorities_rows`
- `schedule_start_hour`
- `schedule_end_hour`
- `notes_fill` (`lines`, `grid`, `dotted-grid`, `millimeter`)

Template plugins:

- Provide local plugin modules with `--template-plugin my.module.path`
- Packaged plugins can register templates via Python entry points (`planner.templates`)

Schedule template notes:

- `schedule` defaults to `06-22` even on `palma` and includes the `22` row.
- `09-18` rows are lightly shaded to distinguish work hours.

All `*-mm` template options are interpreted as physical millimeters and are converted
per device DPI so spacing remains consistent across `remarkable`, `scribe`, and `palma`.

## Theme Customization

Planner and template generation support external theme overrides:

- `--theme-profile <name>`: built-in profile name (`default`)
- `--theme-file <path>`: JSON file with theme overrides

Examples:

```bash
uv run planner --year 2026 --theme-file ./theme.json --output planner_themed.pdf
uv run planner templates generate notes --theme-file ./theme.json --output notes_themed.pdf
```

Theme JSON keys:

- `background`
- `sidebar_bg`
- `sidebar_text`
- `text_primary`
- `text_secondary`
- `accent`
- `grid_lines`
- `writing_lines`
- `link_badge_bg`
- `font_header`
- `font_regular`
- `font_bold`

Minimal example:

```json
{
  "accent": "#112233",
  "grid_lines": "#AAB4BE",
  "font_header": "Helvetica-Bold"
}
```

Invalid keys or invalid color/font values fail fast with a CLI error message.

## Development Commands

```bash
make sync          # sync runtime dependencies from uv.lock
make dev-tools     # install pytest/ruff/pre-commit in .venv
make test-stdlib   # offline-friendly test run (unittest)
make test          # pytest suite (if pytest is installed)
make lint          # ruff checks (if ruff is installed)
make fmt           # ruff formatter (if ruff is installed)
make templates-all # generate all template variants for rm2/scribe/palma
make regression-baseline  # local baseline PDFs+PNGs for visual diffing
make regression-candidate # local candidate PDFs+PNGs for visual diffing
make regression-diff      # threshold-based image comparison report
make regression-clean     # delete local regression artifacts
```

## CI/CD

GitHub Actions workflows are configured for:

- CI on each commit push and pull request:
  - Runs `uv sync --frozen`
  - Runs `make test-stdlib`
- Release on tag push:
  - Runs `make templates-all`
  - Publishes all generated `generated/templates/**/*.pdf` files as release assets

Example release flow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Local Visual Regression

Use `scripts/local_visual_regression.py` (or the `make regression-*` targets) during refactors to
compare current rendering against a local baseline. Artifacts are written under `generated/regression/`
and are local-only guardrails, not a permanent CI requirement.

## Project Layout

- `src/planner/main.py`: CLI and planner orchestration
- `src/planner/components.py`: planner drawing routines that consume computed geometry
- `src/planner/planner_geometry.py`: pure planner geometry calculations
- `src/planner/templates.py`: template registry + generation API
- `src/planner/template_specs.py`: built-in template metadata and registry/spec construction
- `src/planner/template_layout.py`: template layout profiles and unit conversion helpers
- `src/planner/template_renderers.py`: built-in template renderer implementations
- `src/planner/template_engine/`: template contracts, registry, params, and plugin loading
- `src/planner/template_blocks/`: reusable composition blocks
- `src/planner/config.py`: dimensions, palette, and font constants
- `src/planner/profiles.py`: device and layout profile definitions
- `scripts/local_visual_regression.py`: local visual regression workflow helper
- `tests/`: unit and integration tests
