PYTHON ?= python3
BUILD_DIR ?= build

.PHONY: quality test build install editable run docker-build docker-run clean

quality:
	$(PYTHON) -m ruff check PyMieSimX tests
	$(PYTHON) -m mypy PyMieSimX/gui/parsing.py PyMieSimX/gui/schemas.py

test:
	$(PYTHON) -m pytest

build:
	$(PYTHON) -m build --outdir $(BUILD_DIR)

install:
	$(PYTHON) -m pip install .

editable:
	$(PYTHON) -m pip install -e ".[testing,dev]"

run:
	$(PYTHON) -m PyMieSimX --no-browser

docker-build:
	docker build -t pymiesimx .

docker-run:
	docker run --rm -p 8050:8050 pymiesimx

clean:
	rm -rf $(BUILD_DIR) dist *.egg-info .pytest_cache htmlcov .coverage
