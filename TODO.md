# TODO: Rendering Refactor Roadmap

## Legend
- [ ] Not started
- [~] In progress
- [x] Done

## P0 - Tooling Realignment (Prerequisite)
- [x] Update `Makefile` target `templates-all` to use `uv run planner templates generate ...`.
> Comment: The CLI was migrated already; `templates-all` still calls removed `--mode template` flags.
- [x] Update `scripts/local_visual_regression.py` template calls to pass overrides via `param_overrides={...}`.
> Comment: Script still passes removed direct kwargs (for example `notes_fill`), which blocks regression checks.
- [x] Run `make templates-all` and confirm it completes for `remarkable`, `scribe`, and `palma`.
> Comment: This is the gate before architecture work; we need stable generation tooling first.

## P1 - Abstraction Consistency (Big-Bang Rewrite)
- [x] Introduce a shared page render helper used by both planner and templates.
> Comment: One rendering pipeline; planner should stop being a separate imperative branch.
- [x] Refactor planner page composition in `src/planner/main.py` to construct Block trees per page (cover/month/week/day).
> Comment: Keep current page semantics/bookmarks/links; only architecture changes.
- [x] Keep existing component drawing functions but invoke them through Block composition where needed.
> Comment: This avoids visual drift while unifying abstraction.
- [x] Remove duplicated planner-specific render orchestration paths that bypass Block rendering.
> Comment: End state is one page rendering abstraction for both planner and templates.
- [x] Preserve CLI behavior and output file naming during this phase.
> Comment: This phase is architectural unification, not UX changes.

## P2 - ReportLab Decoupling
- [x] Define high-level drawing primitives interface (line/rect/text/fill/path/link primitives).
> Comment: Rendering code should target primitives, not raw ReportLab APIs.
- [x] Add ReportLab adapter implementing primitives.
> Comment: ReportLab remains backend implementation, not architectural dependency.
- [x] Migrate blocks/components/renderers to use primitives interface.
> Comment: This enables future backend/testing flexibility.
- [x] Remove direct ReportLab calls from non-adapter modules.
> Comment: Adapter-only backend coupling.

## P3 - Theme Externalization
- [x] Add theme schema/type (`ThemeProfile`) and loader for external file input.
> Comment: Theme remains centralized but no longer hardcoded-only.
- [x] Add CLI options for theme selection/input (for example `--theme-file` and optional named profile).
> Comment: Keep default visual output identical when no theme file is provided.
- [x] Validate theme input and provide clear CLI errors for missing/invalid keys.
> Comment: Fail fast with explicit diagnostics.
- [x] Document theme customization workflow in `README.md`.
> Comment: Include minimal example config and usage command.

## P4 - Split `templates.py` by Responsibility
- [x] Move template renderer functions into dedicated renderer module(s).
> Comment: Large renderer body should not share file with registry/build/generation orchestration.
- [x] Move template metadata/spec registry construction into dedicated module.
> Comment: Registry/spec logic should be isolated from drawing internals.
- [x] Move layout/unit conversion logic into dedicated module.
> Comment: Layout math and conversions are reusable and testable separately.
- [x] Keep `src/planner/templates.py` as thin facade/re-export layer.
> Comment: Preserve internal call sites while reducing file complexity.

## P5 - Separate Geometry Calculation from Drawing
- [x] Extract planner geometry calculations into pure functions returning typed geometry structures.
> Comment: Geometry should be testable with no PDF/canvas dependency.
- [x] Extract template geometry calculations similarly (lines/grids/schedule/day-at-glance/etc.).
> Comment: Rendering functions should consume computed geometry, not compute inline.
- [x] Add dedicated geometry unit tests for edge cases (small devices, compact layouts, boundary hours/rows).
> Comment: This reduces regression risk during future layout changes.
- [x] Keep drawing functions focused on “render this geometry”, not “compute geometry”.
> Comment: Clear separation improves readability and maintainability.

## Cross-Phase Acceptance Gates
- [x] `make test-stdlib` passes.
- [x] `PYTHONPATH=src .venv/bin/python -m py_compile src/planner/*.py src/planner/template_engine/*.py src/planner/template_blocks/*.py` passes.
- [x] CLI smoke checks pass:
- [x] `uv run planner --year 2026 --output /tmp/planner_2026.pdf`
- [x] `uv run planner templates list`
- [x] `uv run planner templates show notes`
- [x] `uv run planner templates generate notes --param notes_fill=grid --output /tmp/notes_grid.pdf`
- [x] Visual parity gate passes:
- [x] `make regression-baseline`
- [x] `make regression-candidate`
- [x] `make regression-diff`
> Comment: Expected result is exact visual parity for existing outputs in this roadmap.

## Completion Definition
- [x] Planner and template generation share one rendering abstraction.
- [x] Rendering code is backend-decoupled via primitives.
- [x] Theme can be configured externally.
- [x] `templates.py` is split into focused modules.
- [x] Geometry is pure/tested and separated from draw calls.
