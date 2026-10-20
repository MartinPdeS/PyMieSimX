Getting started
===============

Installation
------------

Install the application from PyPI::

   python -m pip install PyMieSimX

PyMieSimX uses PyOptik's material catalogue. Initialize the local catalogue
explicitly when setting up a new environment::

   python -m PyOptik setup --no-progress

Start the dashboard with::

   pymiesimx

The command accepts ``--host``, ``--port``, ``--no-browser``, and ``--debug``.
Run ``pymiesimx --help`` for the complete list.

First workflow
--------------

#. Open **Single scatterer** to configure a wavelength, source, particle, and
   detector.
#. Choose a named material from PyOptik or enter a complex refractive index.
#. Select a measure such as ``Qsca`` or ``Qext`` and press **Run**.
#. Use the plot controls to inspect the result and export the data as CSV.

For parameter studies, use **Parameter scan** to select the varied quantities
and their ranges. PyMieSimX validates the sweep size before submitting it to a
bounded background worker, so the interface remains responsive while a run is
queued or executing.

Python API
----------

The calculation layer is available without creating a Dash application::

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

See :doc:`api` for result-size validation, multiple measures, population
optics, and CSV export helpers.
