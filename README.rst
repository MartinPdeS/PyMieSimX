PyMieSimX
=========

PyMieSimX is the standalone graphical interface for `PyMieSim
<https://github.com/MartinPdeS/PyMieSim>`_. It provides a Dash application for
configuring optical setups, running parameter sweeps, exploring individual
particles, and exporting results.

Installation
------------

Install the GUI and its PyMieSim dependency with::

    pip install PyMieSimX

Launch the dashboard with::

    pymiesimx

Use ``pymiesimx --help`` to see the available host, port, browser, and debug
options.

Development
-----------

Install an editable checkout with::

    pip install -e .

The GUI source lives in ``PyMieSimX/gui``. Scientific calculations are provided
by the installed ``PyMieSim`` package rather than duplicated here.

Testing and automation
----------------------

Run the GUI test suite with::

    pip install -e ".[testing]"
    python -m pytest

GitHub Actions includes quality checks, GUI tests, PyPI publishing, Conda
recipe publishing, and coverage deployment. The Conda recipe is in
``meta.yaml`` and the container entry point is defined in ``Dockerfile``.
