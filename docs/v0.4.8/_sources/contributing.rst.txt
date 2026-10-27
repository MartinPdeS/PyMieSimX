Contributing
============

Install the development dependencies in an editable environment::

   python -m pip install -e ".[testing,dev,docs]"

Run the checks locally with::

   make quality
   make test
   make docs

The project uses Ruff for formatting and linting, mypy for selected typed
modules, and pytest for the GUI and API tests. Pull requests run these checks
through GitHub Actions.
