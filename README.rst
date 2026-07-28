PyMieSimX
=========

PyMieSimX is the standalone graphical interface for `PyMieSim
<https://github.com/MartinPdeS/PyMieSim>`_. It provides a Dash application for
configuring optical setups, running parameter sweeps, exploring individual
particles, and exporting results.

Source-model note
-----------------

The Gaussian source exposed by PyMieSimX is not a generalized Lorenz--Mie
theory (GLMT) implementation. It is a convenience object for defining a
Gaussian illumination through its numerical aperture and optical power in
watts. The ``Gaussian`` and ``GaussianSet`` source options should therefore be
interpreted as a practical source parameterization, not as a separate GLMT
solver.

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

Python API
----------

The computational API can be used without constructing the Dash application::

    from PyMieSimX import run_experiment

    result = run_experiment(
        source_type="GaussianSet",
        source_values={
            "wavelength": "650",
            "polarization": "0",
            "optical_power": "1e-3",
            "numerical_aperture": "0.2",
        },
        scatterer_type="SphereSet",
        scatterer_values={"diameter": "500", "material": "1.4", "medium": "1.0"},
        detector_type="None",
        detector_values={},
        measure="Qsca",
    )

``PyMieSimX.create_dash_app`` and ``PyMieSimX.OpticalSetupGUI`` remain
available for applications that need the graphical interface.

Background calculations and limits
-----------------------------------

Parameter sweeps are submitted to a bounded background worker and reported to
the dashboard through a polling status indicator. Results are guarded by both
an in-memory dataframe limit and a serialized Dash-payload limit. Large-result
warnings are logged before execution; oversized results are rejected with an
actionable message asking you to reduce the sweep.

Run the command-line launcher with ``--debug`` to enable detailed logs. Log
messages use the format ``timestamp | level | logger | message`` and include
experiment job identifiers, input configuration, queue transitions, dataframe
memory usage, and serialized result sizes.

Server-side usage metrics
-------------------------

The dashboard can share a PostgreSQL metrics database with RosettaX. Configure
the Render service with::

    PYMIESIMX_USAGE_METRICS_BACKEND=postgres
    DATABASE_URL=<the shared PostgreSQL URL>

PyMieSimX writes namespaced counters to the shared ``metrics_counters`` table:
``pymiesimx_home_page_visit_count``, ``pymiesimx_experiment_run_count``, and
``pymiesimx_single_run_count``. If PostgreSQL is unavailable, local development
falls back to a JSON file under the platform's application-data directory.
