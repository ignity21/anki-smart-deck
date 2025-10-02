##
# Makefile for catalystx project AnkiSmartDeck
#
# @file
# @version 0.1

.PHONY: test clean-test clean lint lint-fix install install-dev

test:
	uv run pytest -xvs tests/

clean-test:
	rm -rf .pytest_cache
	rm -rf tests/__pycache__
	rm -rf tests/**/__pycache__
	rm -rf .coverage
	rm -rf htmlcov

clean: clean-test
	rm -rf __pycache__

lint:
	uv run ruff check

lint-fix:
	uv run ruff check --fix

install:
	uv pip install

install-dev:
	uv pip install --group dev

help:
	@echo "Available targets:"
	@echo "  test         - Run all tests"
	@echo "  clean        - Clean up all cache files"
	@echo "  clean-test   - Clean up test cache files"
	@echo "  lint         - Run lint checks"
	@echo "  lint-fix     - Fix lint issues"
	@echo "  install      - Install dependencies"
	@echo "  install-dev  - Install development dependencies"

# end
