# Repository Guidelines

## Project Structure & Module Organization
- `src/planner/main.py`: entrypoint and page-generation flow.
- `src/planner/components.py`: reusable drawing primitives (`draw_sidebar`, `draw_header`, `draw_grid`).
- `src/planner/config.py`: page dimensions, color theme, and font constants.
- `pyproject.toml` and `uv.lock`: dependency and Python runtime source of truth.
- `README.md`: project overview (expand it when behavior changes).

Keep new code in `src/planner/`. Put orchestration in `main.py` and keep rendering behavior in focused helper modules.

## Build, Test, and Development Commands
- `uv sync`: install locked dependencies into the local environment.
- `make dev-tools`: install `pytest`, `ruff`, and `pre-commit` into `.venv`.
- `uv run planner --year 2026 --output planner_2026.pdf`: generate the planner PDF locally.
- `make test-stdlib`: run the committed offline-friendly test suite.
- `PYTHONPATH=src .venv/bin/python -m py_compile src/planner/*.py`: fast syntax smoke check.
- `uv lock`: update lockfile after dependency changes.

## Coding Style & Naming Conventions
Use Python 3.14-compatible code and standard PEP 8 defaults:
- 4-space indentation.
- `snake_case` for functions/variables, `UPPER_CASE` for constants.
- Keep layout constants centralized in `config.py`; avoid scattered magic numbers.
- Prefer small, composable drawing functions in `components.py`.
- Add type hints to new public functions and short docstrings where behavior is non-obvious.

## Testing Guidelines
The repository includes tests under `tests/`. New features and bug fixes should add coverage there.
- Test files: `tests/test_<module>.py`
- Test functions: `test_<behavior>()` (or `unittest.TestCase` methods)
- Run tests: `make test-stdlib`

Prioritize coverage for calendar matrix handling, month/page rendering boundaries, and a PDF generation smoke test.

## Commit & Pull Request Guidelines
This repository currently has no shared commit history, so establish a consistent pattern now:
- Commit message format: `<type>: <imperative summary>` (example: `fix: correct config import in main`).
- Keep commits focused, minimal, and runnable.
- PRs should include: purpose, key changes, verification commands, and sample output.
- For visual/PDF changes, attach a screenshot or page excerpt.
- Link related issues when available.
