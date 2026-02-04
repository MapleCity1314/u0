# Repository Guidelines

## Project Structure & Module Organization

- `apps/` runnable user-facing apps (future web/admin).
- `services/` backend APIs and inference services (FastAPI).
- `core/` framework-agnostic algorithms and calculation logic.
- `models/` reusable model definitions.
- `data/` data ingestion, caching, and intermediate artifacts.
- `labs/` experiments and demos; successful work graduates to `core/` or `services/`.
- `infra/` deployment, CI, Docker, IaC.
- `docs/` architecture and product docs.

## Build, Test, and Development Commands

- Install demo deps:
  - `pip install akshare pandas numpy scikit-learn`
- Run the MVP demo:
  - `python labs/fund_nav_rt_022485/main.py` (best during A-share trading hours)
- Run tests:
  - `python -m pytest`

No build system is defined yet (empty `Makefile`, empty `pyproject.toml`). Keep commands project-local and documented here as they are added.

## Coding Style & Naming Conventions

- Primary language: Python.
- Indentation: 4 spaces; line length ~88–100 chars (align with black-compatible style if adopted).
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `ALL_CAPS` for constants.
- Modules: keep `labs/` exploratory; move stable logic to `core/` and `services/`.

## Testing Guidelines

- No test framework or `tests/` directory is currently present.
- When adding tests, prefer `pytest` conventions (`tests/`, `test_*.py`, `*_test.py`) and document the run command here (e.g., `python -m pytest`).
- For model changes, include a small reproducible example or saved output in `labs/`.

## Commit & Pull Request Guidelines

- Commit history shows a simple prefix style: `initial: ...`. Use short, descriptive prefixes (e.g., `feat:`, `fix:`, `docs:`) followed by a concise summary.
- PRs should include: a clear description of the change, linked issue (if any), and demo output or screenshots for `apps/` or `labs/` changes.
- Note data or model assumptions explicitly; avoid committing large raw datasets to `data/`.

## Security & Configuration Tips

- External data sources (e.g., AkShare) may change; keep credentials or tokens out of the repo.
- Prefer environment variables or local config files ignored by git for any secrets.
