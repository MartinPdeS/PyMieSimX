PYTHON ?= python3
RELEASE_KIND := $(or $(BUMP),$(filter major minor patch,$(MAKECMDGOALS)))
BUILD_DIR ?= build

.PHONY: quality test docs build install editable run docker-build docker-run clean release tag patch minor major

quality:
	$(PYTHON) -m ruff check PyMieSimX tests
	$(PYTHON) -m mypy PyMieSimX/gui/parsing.py PyMieSimX/gui/schemas.py PyMieSimX/gui/models.py PyMieSimX/gui/jobs.py PyMieSimX/gui/callback_helpers.py PyMieSimX/gui/admin.py

test:
	$(PYTHON) -m pytest

docs:
	$(PYTHON) -m sphinx -M html docs/source docs/_build

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
	@test "$(words $(RELEASE_KIND))" -eq 1 || { echo "usage: make release [patch|minor|major]" >&2; exit 2; }
	@set -eu; release_tag="$$( $(PYTHON) tools/next_release_version.py $(RELEASE_KIND) )"; \
	$(PYTHON) tools/release_tag.py "$$release_tag"; \
	git push origin HEAD "refs/tags/$$release_tag"

tag:
	$(PYTHON) tools/release_tag.py "$(VERSION)"

patch minor major:
ifeq ($(filter release,$(MAKECMDGOALS)),)
	@$(MAKE) release BUMP=$@
else
	@:
endif

.PHONY: release-check
release-check:
	$(PYTHON) tools/check_release.py $(if $(VERSION),--version $(VERSION),)
