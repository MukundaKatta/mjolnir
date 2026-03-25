.PHONY: test lint clean install help

PYTHON  ?= python3
PYTEST  ?= $(PYTHON) -m pytest
SRC_DIR  = src
TEST_DIR = tests

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

test: ## Run test suite
	PYTHONPATH=$(SRC_DIR) $(PYTEST) $(TEST_DIR) -v --tb=short

install: ## Install in development mode
	$(PYTHON) -m pip install -e ".[dev]"

clean: ## Remove build artefacts
	rm -rf build dist *.egg-info src/*.egg-info __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
