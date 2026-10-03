"""Single-wavelength independent-scattering optics of spherical populations."""

import csv
from io import StringIO

import numpy as np
from PyMieSim import ParticleSizeDistribution
from PyMieSim.experiment import Setup
from PyMieSim.experiment.scatterer_set import SphereSet
from PyMieSim.experiment.source_set import PlaneWaveSet
from PyMieSim.units import ureg

from PyMieSimX.gui.parsing import parse_material_values, parse_polarization, serialize_value


# Native lognormal quadrature becomes nonfinite above 128 nodes in PyMieSim 5.7.1.
MAX_POPULATION_NODES = 128


def _scalar(value, label, *, positive=True):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a single finite number.") from error
    if not np.isfinite(number) or (number <= 0 if positive else number < 0):
        raise ValueError(f"{label} must be finite and {'positive' if positive else 'nonnegative'}.")
    return number


def build_population_distribution(*, distribution="lognormal", diameter_nm=500, width=1.2,
                                  minimum_nm=100, maximum_nm=1000, sampling=128):
    """Build native number fractions; Gaussian width is in nm, lognormal width is GSD."""
    if distribution == "monodisperse":
        return ParticleSizeDistribution.monodisperse(_scalar(diameter_nm, "Diameter") * ureg.nm)
    count = _scalar(sampling, "Distribution sampling")
    if not count.is_integer() or not 16 <= count <= MAX_POPULATION_NODES:
        raise ValueError(f"Distribution sampling must be an integer from 16 to {MAX_POPULATION_NODES}.")
    if distribution == "lognormal":
        median = _scalar(diameter_nm, "Median diameter")
        gsd = _scalar(width, "Geometric standard deviation")
        if not 1 < gsd <= 3:
            raise ValueError("Geometric standard deviation must be greater than 1 and at most 3.")
        return ParticleSizeDistribution.lognormal(median * ureg.nm, gsd, sampling=int(count))
    if distribution not in {"gaussian", "uniform"}:
        raise ValueError("Select monodisperse, Gaussian, lognormal, or uniform.")
    lower = _scalar(minimum_nm, "Minimum diameter")
    upper = _scalar(maximum_nm, "Maximum diameter")
    if upper <= lower:
        raise ValueError("Maximum diameter must exceed minimum diameter.")
    if distribution == "uniform":
        return ParticleSizeDistribution.uniform(lower * ureg.nm, upper * ureg.nm, sampling=int(count))
    mean = _scalar(diameter_nm, "Gaussian mean diameter")
    std = _scalar(width, "Gaussian standard deviation")
    if not lower <= mean <= upper:
        raise ValueError("Gaussian mean must lie within the diameter bounds.")
    return ParticleSizeDistribution.truncated_normal(
        mean * ureg.nm, std * ureg.nm, minimum_diameter=lower * ureg.nm,
        maximum_diameter=upper * ureg.nm, sampling=int(count),
    )


def parse_population_material(value, *, medium=False):
    parsed = parse_material_values(value, medium=medium)
    if parsed is None or isinstance(parsed, (list, tuple, np.ndarray)):
        raise ValueError("Material and medium must each be one refractive index or material name.")
    if isinstance(parsed, (int, float, complex)):
        index = complex(parsed)
        if not np.isfinite(index) or index.real <= 0 or index.imag < 0 or (medium and index.imag != 0):
            raise ValueError("Use a positive real medium index and a particle index n+ik with n > 0 and k >= 0.")
        return index.real if medium else index
    return parsed


def compute_population_optics(*, wavelength_nm=650, material="1.5+0.01j", medium="1.33",
                              distribution="lognormal", diameter_nm=500, width=1.2,
                              minimum_nm=100, maximum_nm=1000, sampling=128,
                              concentration=1e9, concentration_basis="number"):
    """Return all population properties as JSON-safe values with explicit units.

    Diameters and vacuum wavelength are in nm. Number concentration is particles/mL;
    volume concentration is a fraction from 0 to 1. Cross sections are per particle.
    Gaussian distributions are truncated and renormalized within the supplied bounds.
    Undefined albedo and anisotropy are returned as None. Host absorption is excluded.
    """
    wavelength = _scalar(wavelength_nm, "Vacuum wavelength")
    concentration = _scalar(concentration, "Concentration", positive=False)
    if concentration_basis not in {"number", "volume"}:
        raise ValueError("Concentration basis must be number or volume.")
    if concentration_basis == "volume" and concentration > 1:
        raise ValueError("Particle volume fraction must be between 0 and 1.")
    particles = build_population_distribution(
        distribution=distribution, diameter_nm=diameter_nm, width=width,
        minimum_nm=minimum_nm, maximum_nm=maximum_nm, sampling=sampling,
    )
    diameters = np.asarray(particles.diameters.to("meter").magnitude)
    weights = np.asarray(particles.number_fractions)
    if not np.all(np.isfinite(diameters)) or np.max(diameters) / (wavelength * 1e-9) > 1000:
        raise ValueError("Largest sampled diameter must be at most 1000 times the wavelength.")
    particle_material = parse_population_material(material)
    host = parse_population_material(medium, medium=True)
    mean_volume = float(weights @ (np.pi / 6 * diameters ** 3))
    mean_area = float(weights @ (np.pi / 4 * diameters ** 2))
    if not np.isfinite(mean_volume) or not np.isfinite(mean_area) or mean_volume <= 0 or mean_area <= 0:
        raise ValueError("Particle dimensions are outside the supported numerical range.")
    number_density = concentration * 1e6 if concentration_basis == "number" else concentration / mean_volume
    volume_fraction = number_density * mean_volume
    if not np.isfinite(number_density) or not np.isfinite(volume_fraction) or volume_fraction > 1:
        raise ValueError("Concentration implies a particle volume fraction above 1 or a nonfinite number density.")
    setup = Setup(
        source_set=PlaneWaveSet(wavelength=wavelength * ureg.nm,
                                polarization=parse_polarization("0", ureg.degree), amplitude=1 * ureg.volt / ureg.meter),
        scatterer_set=SphereSet(diameter=particles.diameters, material=particle_material, medium=host),
    )
    measures = ("Csca", "Cabs", "Cext", "Qsca", "Qabs", "Qext")
    averaged = setup.average_size_distribution(particles, *measures)
    values = dict(zip(measures, np.asarray(averaged.as_numpy()).reshape(-1).tolist()))
    if not all(np.isfinite(value) for value in values.values()):
        raise ValueError("The solver returned nonfinite optical properties. Check the inputs.")
    # A matched constant index has no optical contrast; discard solver roundoff.
    matched = isinstance(particle_material, complex) and isinstance(host, (int, float)) and particle_material == host
    if matched:
        values = dict.fromkeys(measures, 0.0)
    # Roundoff can produce tiny negative absorption for lossless particles.
    tolerance = 1e-10 * max(values["Cext"], values["Csca"], mean_area)
    if values["Cabs"] < -tolerance or values["Csca"] < 0:
        raise ValueError("The solver returned negative scattering or absorption.")
    values["Cabs"] = max(0.0, values["Cabs"])
    values["Cext"] = values["Csca"] + values["Cabs"]
    values["Qabs"] = values["Cabs"] / mean_area
    values["Qext"] = values["Cext"] / mean_area
    g = None
    if values["Csca"] > 0:
        g = float(np.asarray(setup.average_size_distribution(particles, "g").as_numpy()).item())
        if not np.isfinite(g):
            raise ValueError("The solver returned nonfinite anisotropy.")
    q_number = np.asarray(setup.run("Qsca", "Qabs", "Qext").as_numpy()).reshape(3, -1) @ weights
    if matched:
        q_number[:] = 0
    if not np.all(np.isfinite(q_number)):
        raise ValueError("The solver returned nonfinite averaged efficiencies.")
    rows = []

    def add(parameter, value, unit, definition):
        rows.append({"parameter": parameter, "value": value, "unit": unit, "definition": definition})

    for name, cross in (("mu_s", "Csca"), ("mu_a", "Cabs"), ("mu_ext", "Cext")):
        add(name, number_density * values[cross] / 1000, "mm^-1", f"Number density × mean {cross}; particle contribution")
    add("mu_s_prime", number_density * values["Csca"] / 1000 * (1 - g) if g is not None else 0.0,
        "mm^-1", "Reduced scattering: mu_s × (1 − effective g)")
    add("albedo", values["Csca"] / values["Cext"] if values["Cext"] > 0 else None,
        "dimensionless", "Population single-scattering albedo: mean Csca / mean Cext")
    add("g", g, "dimensionless", "Anisotropy weighted by scattering cross section")
    for name in ("Csca", "Cabs", "Cext"):
        add(f"mean_{name}", values[name] * 1e18, "nm^2", "Number-averaged cross section per particle")
    for name, number_mean in zip(("Qsca", "Qabs", "Qext"), q_number):
        add(f"mean_{name}_number", float(number_mean), "dimensionless", "Number-averaged efficiency")
        add(f"mean_{name}_area", values[name], "dimensionless", "Mean cross section / mean projected area")
    add("number_concentration", number_density / 1e6, "particles/mL", "Total particle number concentration")
    add("volume_fraction", volume_fraction, "dimensionless", "Number density × number-averaged particle volume")
    add("mean_diameter", float(weights @ diameters) * 1e9, "nm", "Number-averaged diameter")
    return {
        "results": rows,
        "distribution": {"diameters_nm": (diameters * 1e9).tolist(), "number_fractions": weights.tolist()},
        "inputs": {"wavelength_nm": wavelength, "material": str(material), "medium": str(medium),
                   "distribution": distribution, "diameter_nm": serialize_value(diameter_nm), "width": serialize_value(width),
                   "minimum_nm": serialize_value(minimum_nm), "maximum_nm": serialize_value(maximum_nm), "sampling": serialize_value(sampling),
                   "concentration": concentration, "concentration_basis": concentration_basis},
        "approximation": "Independent scattering of homogeneous spheres; host-medium absorption excluded.",
    }


def export_population_to_csv(result):
    """Export results, units, definitions, input provenance, and discrete number fractions."""
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["parameter", "value", "unit", "definition"])
    for row in result["results"]:
        writer.writerow([row[key] for key in ("parameter", "value", "unit", "definition")])
    writer.writerow([])
    writer.writerow(["approximation", result["approximation"]])
    writer.writerow(["input", "value"])
    writer.writerows(result["inputs"].items())
    writer.writerow([])
    writer.writerow(["diameter_nm", "number_fraction"])
    writer.writerows(zip(result["distribution"]["diameters_nm"], result["distribution"]["number_fractions"]))
    return output.getvalue()
