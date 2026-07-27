# Repository Guidelines

## Project Structure & Module Organization
Source code lives under `src/ankinote/`. Key areas include `cli/` for the command-line entrypoints, `services/` for external integrations, `utils/` for shared helpers, and `collections/` for card-generation logic, templates, prompts, and assets. Tests live in `tests/` and follow the same package layout where practical, such as `tests/utils/test_httpcli.py`. Keep generated files, caches, and virtual environments out of the tree.

## Build, Test, and Development Commands
Use `uv` for dependency and task execution.

- `make test` or `uv run pytest`: run the full test suite.
- `make format` or `uv run ruff format`: format Python code.
- `make lint` or `uv run ruff check --fix`: apply lint fixes.
- `make check` or `uv run basedpyright`: run static type checks.
- `make clean-test`: remove pytest and coverage caches.

## Coding Style & Naming Conventions
Target Python 3.13+ and keep code compatible with the configured tooling in `pyproject.toml`. Use 88-character line length, standard Ruff formatting, and standard type hints. Prefer `snake_case` for functions, modules, and filenames; use `PascalCase` for classes. Match existing module names such as `httpcli.py`, `generator.py`, and `collection.py`.

## Testing Guidelines
Pytest is the test runner, with async support enabled via `pytest-asyncio`. Place tests in `tests/` and name them `test_*.py`. Prefer focused unit tests for CLI logic, generators, and utilities, and add fixtures only when they reduce duplication. Run `make test` before opening a pull request.

## Commit & Pull Request Guidelines
Recent commits use short, descriptive messages with optional conventional prefixes such as `fix:`, `refactor:`, `chore:`, or `feat:`. Keep commit subjects imperative and specific. Pull requests should include a brief summary, the commands used to verify changes, and screenshots or sample output when behavior changes affect generated cards or CLI output.

## Configuration & Secrets
Local configuration is expected through environment variables such as `GEMINI_API_KEY`, `GOOGLE_TTS_KEY`, and `ANKI_CONNECT_URL`. Do not commit `.env` files or API keys. When adding new integrations, document required settings in `README.md` and keep defaults safe for local development.
