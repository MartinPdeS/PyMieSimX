"""Calculate the scattering efficiency of a single sphere."""

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
print(result["rows"][0]["Qsca"])
