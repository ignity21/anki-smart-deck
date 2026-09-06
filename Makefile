##
# Makefile for ankinote-ai
#
# @file
# @version 0.2

.PHONY: test clean-test clean lint check format pre-commit help \
        build publish clean-dist bump-version \
        install install-dev

clean-test:
	rm -rf .pytest_cache
	rm -rf tests/__pycache__
	rm -rf tests/**/__pycache__
	rm -rf .coverage
	rm -rf htmlcov

test:
	uv run pytest

clean: clean-test
	rm -rf __pycache__

lint:
	uv run ruff check --fix

check:
	uv run ty check

format:
	uv run ruff format

pre-commit: format lint check

install:
	uv pip install

install-dev:
	uv pip install --group dev

clean-dist:
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info

build: clean-dist
	uv build

publish: build
	uv publish

bump-version:
	@test -n "$(part)" || (echo "Usage: make bump-version part=<major|minor|patch>" && exit 1)
	hatch version $(part)

help:
	@echo "Available targets:"
	@echo "  test         - Run all tests"
	@echo "  clean        - Clean up all cache files"
	@echo "  clean-test   - Clean up test cache files"
	@echo "  lint         - Run lint checks"
	@echo "  check        - Run static type checks"
	@echo "  format       - Format code with ruff"
	@echo "  pre-commit   - Run format, lint, and check"
	@echo "  build        - Build wheel and sdist"
	@echo "  publish      - Build and publish to PyPI"
	@echo "  bump-version - Bump version (part=patch|minor|major)"
	@echo "  install      - Install dependencies"
	@echo "  install-dev  - Install development dependencies"

# end of Makefile
