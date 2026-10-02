# Working on PyMieSimX

PyMieSimX provides a Dash GUI and Python API for PyMieSim. The hosted service is
https://pymiesim.onrender.com/. Keep browser use, local installation, and the
Python API working together.

## Repository map

- `PyMieSimX/api.py` exposes the computational API. Preserve compatibility for
  single-measure callers when extending sweep results.
- `PyMieSimX/gui/computation.py`, `parsing.py`, `validation.py`, and `schemas.py`
  handle scientific inputs, calculations, result serialization, and plotting.
  Delegate scientific solvers to PyMieSim and optical materials to PyOptik.
- `PyMieSimX/gui/jobs.py` manages bounded background sweep jobs;
  `callbacks.py` connects job state, validation, plotting, and exports to Dash.
- `PyMieSimX/gui/pages/`, `components/`, and `layout.py` compose the interface.
  CSS and browser assets live in `PyMieSimX/gui/assets/`.
- `PyMieSimX/application/wsgi.py` is the hosted-server entry point;
  `PyMieSimX/__main__.py` provides the `pymiesimx` launcher.
- `tests/gui/` covers Python behavior and Dash callbacks. `tests/browser/`
  exercises the real browser workflow separately.

## Setup and checks

Use Python 3.11 or newer and a virtual environment. Reuse an existing suitable
environment when available; do not modify sibling repositories to set up this
one.

```sh
python -m pip install -e ".[testing,dev,browser]"
python -m PyOptik setup --no-progress
make quality PYTHON=python
python -m pytest
python -m pytest tests/browser --config-file=pytest.ini --headless --cov=PyMieSimX --cov-report=term --cov-fail-under=0
git diff --check
```

Browser tests need Chrome and a compatible ChromeDriver. The default pytest
suite runs `tests/gui` and enforces the coverage threshold in `.coveragerc`;
the separate browser command intentionally disables that threshold. Use a
writable `MPLCONFIGDIR` when the default Matplotlib cache is unavailable.

Run checks relevant to the change. For UI interaction changes, run the browser
suite as well as affected callback tests. Wait for observable UI state and CSS
transitions; avoid fixed sleeps, JavaScript clicks that bypass actual hit
testing, or removing assertions to make tests pass. Use explicit viewport sizes
when testing desktop and responsive layouts.

## Implementation conventions

- Use four spaces and follow the existing Python style. Keep Ruff and the
  scoped Mypy checks in `make quality` passing.
- Keep parsing and scientific computation separate from Dash rendering so the
  public Python API remains usable without constructing a GUI.
- Preserve physical units, dataframe index information, and all selected
  measures through serialization, plotting, and CSV export.
- Validate sweep and result-size limits before expensive work where possible.
  Keep queued/running/completed/error states visible and make Run recover after
  validation failures, missing jobs, cancellation, and computation errors.
- Keep usage metrics optional for local runs and protect the administration
  page with its server-side token. Never commit database URLs or secrets.
- Add regression coverage for behavior changes; use asymmetric data when
  checking axis orientation and multiple measures when checking sweep output.

## Documentation, packaging, and CI

- `README.rst` uses reStructuredText. Check new sections and links render
  correctly, including heading underline lengths.
- Dependencies and the console entry point are declared in `pyproject.toml`.
  Keep `conda.recipe/meta.yaml` consistent with them. Conda builds are
  platform-specific for Python 3.11–3.13 on Linux, macOS, and Windows; retain
  the Windows dependency selectors and explicit `pymiesimx` entry point.
- The Conda workflow supports manual build verification. Publishing to Conda
  and PyPI occurs on version-tag pushes. Verify the installed Conda artifact,
  including both import and CLI startup, rather than only the checkout.
- Versions come from Git tags through setuptools-scm. Use the existing release
  tools/Makefile when a release is requested; a normal commit/push does not
  imply creating a release tag.
- Inspect failing Actions job logs and fix the underlying cause. After pushing
  a CI fix, check the run for the new commit and report any remaining failures.
- Preserve unrelated working-tree changes and commit only the requested work.
