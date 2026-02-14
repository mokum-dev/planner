PYTHONPATH ?= src
PYTHON ?= .venv/bin/python
UV_CACHE_DIR ?= /tmp/uv-cache
TEMPLATE_OUTPUT_DIR ?= generated/templates

.PHONY: sync dev-tools run test test-stdlib lint fmt check templates-all regression-baseline regression-candidate regression-diff regression-clean

sync:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync

dev-tools:
	uv pip install --python $(PYTHON) pytest ruff pre-commit

run:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run planner

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -q

test-stdlib:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -q

lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m ruff check src tests

fmt:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m ruff format src tests

check: lint test

templates-all:
	@set -eu; \
	for mapping in "rm2:remarkable" "scribe:scribe" "palma:palma"; do \
		device_label=$${mapping%%:*}; \
		device_name=$${mapping##*:}; \
		output_dir="$(TEMPLATE_OUTPUT_DIR)/$${device_label}"; \
		mkdir -p "$$output_dir"; \
		for template in lines grid dotted-grid day-at-glance schedule task-list todo-list; do \
			template_name=$$(printf "%s" "$$template" | tr '-' '_'); \
			UV_CACHE_DIR=$(UV_CACHE_DIR) uv run planner templates generate "$$template" --device "$$device_name" --output "$$output_dir/$${template_name}.pdf"; \
		done; \
		for notes_fill in lines grid dotted-grid millimeter; do \
			fill_name=$$(printf "%s" "$$notes_fill" | tr '-' '_'); \
			UV_CACHE_DIR=$(UV_CACHE_DIR) uv run planner templates generate notes --device "$$device_name" --param notes_fill="$$notes_fill" --output "$$output_dir/notes_$${fill_name}.pdf"; \
		done; \
		done

regression-baseline:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/local_visual_regression.py baseline

regression-candidate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/local_visual_regression.py candidate

regression-diff:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/local_visual_regression.py diff

regression-clean:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/local_visual_regression.py clean
