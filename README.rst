PyMieSimX
=========

PyMieSimX is the standalone graphical interface for `PyMieSim
<https://github.com/MartinPdeS/PyMieSim>`_. It provides a Dash application for
configuring optical setups, running parameter sweeps, exploring individual
particles, and exporting results.

Try the live webapp
----------------------

**Run Mie scattering simulations in your browser—no installation required.**

.. image:: https://img.shields.io/badge/Launch_Webapp-Open_in_browser-2672d6?style=for-the-badge
   :target: https://pymiesim.onrender.com/
   :alt: Launch the PyMieSimX webapp in your browser

`Launch the PyMieSimX webapp <https://pymiesim.onrender.com/>`_ to configure
optical setups, run parameter sweeps, explore individual particles, and download
your results as CSV files. The hosted service provides direct access to the
graphical interface; local installation is also available below.

Examples
--------

The **Examples** page provides six starting points: gold and silver nanoparticle
resonances, a silica size sweep, gold nanoshells, a bead's angular scattering,
and a polydisperse silica suspension. Each card links to its simulation
workspace, restores the complete setup, and runs automatically to show results.
The parameters can then be adjusted and the results exported as CSV.

Sharing simulations
-------------------

Use **Copy simulation link** in Single Scatterer, Parameter Scan, or Ensemble
Optics to share the current setup. Links preserve the input values, sweep
ranges, selected measures, and plot settings without requiring an account.
Opening a link restores the setup and automatically runs the simulation once
the inputs and plot settings are ready. Later edits can be calculated with
**Run**. Copying puts the link directly on the clipboard and briefly shows
**Copied** on the button without displaying an additional card.

Links store the configuration rather than a result snapshot. Recalculation
uses the installed solver and optical material data, so results can change
after those dependencies are updated.

Ensemble Optics
---------------

Open **Ensemble Optics** to compute the properties of a homogeneous spherical
particle population at one vacuum wavelength, without a parameter sweep. The
collapsible Particle, Distribution, and Concentration side tabs hold the inputs;
the Model tab explains the assumptions and averaging. Choose a monodisperse,
truncated Gaussian, lognormal, or uniform number-based diameter distribution
and supply a number concentration (particles/mL) or volume fraction.
Gaussian width is a standard deviation in nm; lognormal width is a geometric
standard deviation (greater than 1 and at most 3). Gaussian bounds are positive
and the distribution is renormalized within them. Named optical materials are
resolved through PyOptik, or you can enter a particle index ``n+ik`` and a real
medium index directly. Both fields use the same RI/Material toggle as the other
workspaces; switching back to RI restores the previously entered index.

Results include scattering, particle absorption, extinction, reduced scattering
(in inverse millimeters), population single-scattering albedo, effective
anisotropy, averaged cross sections, and both number- and area-weighted
efficiencies. Cross sections are number averages; area efficiencies divide mean
cross section by mean projected area. Effective anisotropy is weighted by
scattering cross section. Population albedo is mean scattering cross section
divided by mean extinction cross section, rather than a number average of
individual albedos. Undefined ratios are displayed as undefined.

The calculation assumes independent scattering and excludes particle
interactions, multiple scattering, and host-medium absorption. Use dilute
populations. Preview the discrete number fractions, increase sampling to check
convergence, and export results with units, definitions, inputs, and weights.
PyMieSim 5.7.1 or newer supplies the distribution and averaging routines.

The same calculation is available without constructing the GUI::

    from PyMieSimX import compute_population_optics, export_population_to_csv

    result = compute_population_optics(
        wavelength_nm=650,
        material="1.5+0.01j",
        medium="1.33",
        distribution="lognormal",
        diameter_nm=500,
        width=1.2,
        concentration=1e9,
        concentration_basis="number",
    )
    csv_text = export_population_to_csv(result)

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

Install the GUI with PyMieSim and PyOptik with::

    pip install PyMieSimX

The first ``pymiesimx`` launch downloads PyOptik's complete
RefractiveIndex.INFO snapshot. It can also be initialized explicitly with::

    python -m PyOptik setup --no-progress

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

Multiple measures
-----------------

The Parameter Scan Measures selector accepts several quantities in one run.
For example, select ``Qsca``, ``Qabs``, and ``Qext`` to compare scattering,
absorption, and extinction efficiencies. Measures with the same units share a
plot; different units use separate panels with a shared X axis. CSV exports
contain a column for each computed measure.

The Python API accepts either a single name or a list, for example
``run_experiment(..., measure=["Qsca", "Qabs", "Qext"])``. Results include
``measures`` with every computed name; ``measure`` retains the first name for
compatibility with existing single-measure callers. Size validation accounts
for the additional result columns.

Background calculations and limits
-----------------------------------

Parameter sweeps are submitted to a bounded background worker and reported to
the dashboard with visible queued, running, completed, and error messages beside
Run. The completed-run card shows the number of result rows. Oversized sweeps are
rejected with guidance when you click Run. Results are guarded by both an
in-memory dataframe limit and a serialized Dash-payload limit, with estimated
size validation before execution and actual size checks after computation.

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
``pymiesimx_single_run_count``. Metrics are collected only when the PostgreSQL
backend is explicitly configured and available. Local installations do not
persist usage counters.

To show a small **Webapp visits** box in the homepage's top card, set this
environment variable on the Render service and redeploy::

    SHOW_METRIC=true

The box is hidden by default and requires the PostgreSQL configuration above.
It shows the total home-page visit count, including repeat visits, rather than
unique visitors. If the database is unavailable, the box stays hidden.

Administration page
-------------------

Detailed usage counters are shown on the hidden, token-protected administration
page. Configure a server-side token with::

    PYMIESIMX_ADMIN_TOKEN=<a long random value>

Then open ``/admin?token=<the same value>``. The page is intentionally absent
from the public sidebar and refreshes its counters every 30 seconds.
