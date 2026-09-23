PYTHON ?= python3
BUILD_DIR ?= build

.PHONY: quality test build install editable run docker-build docker-run clean release tag patch minor major

quality:
	$(PYTHON) -m ruff check PyMieSimX tests
	$(PYTHON) -m mypy PyMieSimX/gui/parsing.py PyMieSimX/gui/schemas.py PyMieSimX/gui/models.py PyMieSimX/gui/jobs.py PyMieSimX/gui/callback_helpers.py PyMieSimX/gui/admin.py

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

release:
	@set -eu; release_tag="$$( $(PYTHON) tools/next_release_version.py $(BUMP) )"; \
	$(PYTHON) tools/release_tag.py "$$release_tag"; \
	git push origin HEAD "refs/tags/$$release_tag"

tag:
	@set -eu; release_tag="$$( $(PYTHON) tools/next_release_version.py $(BUMP) )"; \
	$(PYTHON) tools/release_tag.py "$$release_tag"

patch minor major:
	@$(MAKE) release BUMP=$@
