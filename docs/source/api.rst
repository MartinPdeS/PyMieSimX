Python API
==========

The top-level API is independent of the Dash server and is useful in scripts,
notebooks, and automated workflows.

.. autosummary::
   :toctree: generated

   PyMieSimX.api.run_experiment
   PyMieSimX.api.compute_population_optics
   PyMieSimX.api.validate_experiment_inputs
   PyMieSimX.api.available_measures
   PyMieSimX.api.export_result_to_csv
   PyMieSimX.api.export_single_result_to_csv
   PyMieSimX.api.export_population_to_csv
   PyMieSimX.api.estimate_result_size
   PyMieSimX.api.estimate_sweep_size

Population example
------------------

Calculate bulk optical properties for a lognormal population and export the result::

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

API module
----------

.. automodule:: PyMieSimX.api
   :no-members:
   :show-inheritance:
