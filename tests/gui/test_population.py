"""Regression coverage for population weighting, units, and the dedicated page."""

import json
from types import SimpleNamespace
from io import StringIO

import numpy as np
import pandas as pd
import pytest
from dash import no_update
from dash.exceptions import PreventUpdate
from PyMieSim.single import Setup
from PyMieSim.single.scatterer import Sphere
from PyMieSim.single.source import PlaneWave
from PyMieSim.units import ureg

from PyMieSimX import compute_population_optics, export_population_to_csv
from PyMieSimX.gui.interface import create_dash_app
from PyMieSimX.gui.population_service import build_population_distribution
from tests.gui.test_dash_callbacks import _callback


def _values(result):
    return {row["parameter"]: row["value"] for row in result["results"]}


def _single(diameter):
    setup = Setup(scatterer=Sphere(diameter=diameter * ureg.nm, material=1.5+0.01j, medium=1.33),
                  source=PlaneWave(wavelength=650 * ureg.nm, polarization=0 * ureg.degree,
                                   amplitude=1 * ureg.volt / ureg.meter))
    return {name: float(setup.get(name).magnitude) for name in ("Csca", "Cabs", "Cext", "Qsca", "g")}


def test_monodisperse_matches_single_solver_and_units():
    result = compute_population_optics(distribution="monodisperse", concentration=1e9)
    values = _values(result)
    single = _single(500)
    assert values["mu_s"] == pytest.approx(single["Csca"] * 1e12)
    assert values["mu_a"] == pytest.approx(single["Cabs"] * 1e12)
    assert values["mean_Csca"] == pytest.approx(single["Csca"] * 1e18)
    assert values["mean_Qsca_number"] == pytest.approx(single["Qsca"])
    assert values["mean_Qsca_area"] == pytest.approx(single["Qsca"])
    assert values["g"] == pytest.approx(single["g"])
    assert values["albedo"] == pytest.approx(single["Csca"] / single["Cext"])
    assert values["mu_s_prime"] == pytest.approx(values["mu_s"] * (1-values["g"]))
    assert values["mu_ext"] == pytest.approx(values["mu_s"] + values["mu_a"])
    assert result["results"][0]["unit"] == "mm^-1"
    json.dumps(result, allow_nan=False)
    json.dumps(compute_population_optics(sampling=np.int64(32)), allow_nan=False)


def test_distribution_uses_cross_section_weighted_ratios():
    result = compute_population_optics(distribution="uniform", minimum_nm=100, maximum_nm=900, sampling=16)
    values = _values(result)
    weights = np.array(result["distribution"]["number_fractions"])
    diameters = np.array(result["distribution"]["diameters_nm"])
    singles = [_single(diameter) for diameter in diameters]
    csca = np.array([item["Csca"] for item in singles])
    cext = np.array([item["Cext"] for item in singles])
    g = np.array([item["g"] for item in singles])
    qsca = np.array([item["Qsca"] for item in singles])
    assert values["g"] == pytest.approx(weights @ (csca*g) / (weights @ csca))
    assert values["albedo"] == pytest.approx(weights @ csca / (weights @ cext))
    assert values["albedo"] != pytest.approx(weights @ (csca/cext))
    assert values["mean_Qsca_number"] == pytest.approx(weights @ qsca)
    assert values["mean_Qsca_area"] == pytest.approx(weights @ csca / (weights @ (np.pi/4*(diameters*1e-9)**2)))
    assert values["mean_Qsca_number"] != pytest.approx(values["mean_Qsca_area"])


def test_concentration_conversion_scaling_and_zero():
    base = _values(compute_population_optics())
    doubled = _values(compute_population_optics(concentration=2e9))
    volume = _values(compute_population_optics(concentration_basis="volume", concentration=base["volume_fraction"]))
    zero = _values(compute_population_optics(concentration=0))
    for name in ("mu_s", "mu_a", "mu_ext", "mu_s_prime"):
        assert doubled[name] == pytest.approx(2*base[name])
        assert volume[name] == pytest.approx(base[name])
        assert zero[name] == 0
    assert volume["number_concentration"] == pytest.approx(1e9)
    for name in ("albedo", "g", "mean_Qsca_number", "mean_Csca"):
        assert doubled[name] == pytest.approx(base[name])
        assert zero[name] == pytest.approx(base[name])


@pytest.mark.parametrize("distribution,width", [("monodisperse", 1.2), ("lognormal", 1.2), ("gaussian", 70), ("uniform", 1.2)])
def test_native_distributions_are_normalized_positive_and_serializable(distribution, width):
    particles = build_population_distribution(distribution=distribution, width=width)
    assert np.sum(particles.number_fractions) == pytest.approx(1)
    assert np.all(particles.diameters.magnitude > 0)
    assert np.all(particles.number_fractions >= 0)
    if distribution in {"gaussian", "uniform"}:
        assert np.all(particles.diameters.to("nm").magnitude >= 100)
        assert np.all(particles.diameters.to("nm").magnitude <= 1000)
    result = compute_population_optics(distribution=distribution, width=width)
    json.dumps(result, allow_nan=False)


def test_lognormal_narrow_limit_and_convergence():
    mono = _values(compute_population_optics(distribution="monodisperse"))
    narrow = _values(compute_population_optics(width=1.0001))
    fine = _values(compute_population_optics(sampling=128))
    standard = _values(compute_population_optics(sampling=64))
    assert narrow["mu_s"] == pytest.approx(mono["mu_s"], rel=1e-5)
    assert fine["mu_s"] == pytest.approx(standard["mu_s"], rel=1e-3)


def test_lossless_matched_and_named_materials():
    assert _values(compute_population_optics(material="1.5"))["albedo"] == pytest.approx(1)
    matched = _values(compute_population_optics(material="1.33"))
    assert matched["mu_s"] == matched["mu_a"] == matched["mu_s_prime"] == 0
    assert matched["g"] is None and matched["albedo"] is None
    assert _values(compute_population_optics(material="fused_silica"))["mu_s"] > 0


@pytest.mark.parametrize("kwargs", [
    {"wavelength_nm": "600:700:3"}, {"wavelength_nm": 0}, {"wavelength_nm": None},
    {"wavelength_nm": float("nan")}, {"concentration": -1}, {"concentration": 1e30},
    {"concentration_basis": "mass"}, {"concentration_basis": "volume", "concentration": 1.1},
    {"distribution": "other"}, {"sampling": 257}, {"sampling": 15}, {"sampling": 16.5},
    {"width": 1}, {"width": 3.1}, {"diameter_nm": -5},
    {"distribution": "gaussian", "minimum_nm": -1},
    {"distribution": "uniform", "minimum_nm": 1000, "maximum_nm": 100},
    {"distribution": "gaussian", "diameter_nm": 2000}, {"distribution": "gaussian", "width": 0},
    {"material": "1.5,1.6"}, {"material": ""}, {"material": "1.5-0.01j"},
    {"medium": "1.33+0.1j"}, {"medium": "0"}, {"material": "nan"},
    {"distribution": "monodisperse", "diameter_nm": 1e9},
])
def test_invalid_inputs_are_rejected(kwargs):
    with pytest.raises(ValueError):
        compute_population_optics(**kwargs)


def test_export_retains_properties_units_and_distribution():
    result = compute_population_optics()
    csv_text = export_population_to_csv(result)
    frame = pd.read_csv(StringIO(csv_text.split("\n\n")[0]))
    assert frame["parameter"].tolist() == [row["parameter"] for row in result["results"]]
    assert frame.loc[0, "unit"] == "mm^-1"
    assert "wavelength_nm,650" in csv_text
    assert "diameter_nm,number_fraction" in csv_text
    assert len(csv_text.split("diameter_nm,number_fraction")[1].strip().splitlines()) == 128


def test_population_route_callbacks_validation_recovery_and_export(monkeypatch):
    app = create_dash_app()
    route = _callback(app, "_route_pages")("/population", "", 0, 0, 0, {}, {})
    assert route[-2].endswith("active")
    controls = _callback(app, "_population_distribution_controls")
    for distribution in ("gaussian", "uniform", "monodisperse", "lognormal"):
        assert len(controls(distribution)) == 8
    assert _callback(app, "_population_concentration_controls")("volume")[1] == "0.001"
    assert _callback(app, "_population_concentration_controls")("number")[1] == "1e9"
    preview = _callback(app, "_population_preview")
    assert len(preview("gaussian", "500", "50", "100", "1000", "128", {"theme": "dark"})[0].data) == 1
    lognormal_plot, error = preview("lognormal", "500", "1.2", "100", "1000", "128", {})
    assert error == ""
    assert lognormal_plot.layout.xaxis.range[1] < 2000
    assert preview("gaussian", "500", "0", "100", "1000", "128", {})[1]
    compute = _callback(app, "_compute_population")
    args = ["650", "1.5+0.01j", "1.33", "lognormal", "500", "1.2", "100", "1000", "128", "number", "1e9"]
    with pytest.raises(PreventUpdate):
        compute(0, *args)
    failed = compute(1, "invalid", *args[1:])
    assert failed[0] is None and failed[3] is True
    completed = compute(2, *args)
    assert completed[0] and completed[3] is False
    assert "Completed" in completed[2]
    export = _callback(app, "_export_population")
    assert export(0, None) is no_update
    assert "mu_s" in export(1, completed[0])["content"]
    assert _callback(app, "_invalidate_population")(*args)[0] is None
    monkeypatch.setattr("PyMieSimX.gui.pages.population.compute_population_optics", lambda **kwargs: 1/0)
    assert "Computation failed" in compute(3, *args)[2]



def test_population_sidebar_uses_shared_open_switch_and_dismiss_behavior(monkeypatch):
    from PyMieSimX.gui import callbacks

    handle = _callback(create_dash_app(), "_handle_population_sidebar_tabs")

    def click(target, current_class="right-sidebar-panel", active=None):
        monkeypatch.setattr(callbacks, "ctx", SimpleNamespace(
            triggered_id=target, triggered_prop_ids={f"{target}.n_clicks": target},
        ))
        return handle(0, 0, 0, 0, 0, 0, 0, current_class, active)

    particle = click("population-tab-particle")
    assert particle[:2] == ("right-sidebar-panel open", "population-tab-particle")
    assert particle[2].endswith("active")
    assert particle[6:] == ({}, {"display": "none"}, {"display": "none"}, {"display": "none"})
    distribution = click("population-tab-distribution", *particle[:2])
    assert distribution[7] == {} and distribution[6] == {"display": "none"}
    assert distribution[3].endswith("active")
    inside = click("population-right-sidebar", *distribution[:2])
    assert all(value is no_update for value in inside)
    for target in ("population-tab-distribution", "page-content", "dashboard-sidebar"):
        dismissed = click(target, *distribution[:2])
        assert dismissed[0] == "right-sidebar-panel"
        assert all(style == {"display": "none"} for style in dismissed[6:])


@pytest.mark.parametrize("ri", ["1.5+0.01j", "1.45e0", "1.33"])
def test_shared_material_toggle_preserves_numeric_indices(ri):
    from PyMieSimX.gui.layout import render_field
    from PyMieSimX.gui.schemas import FieldSpec

    field = render_field("population", FieldSpec("material", "Material", "material", ri))
    assert field.children[1].className == "material-mode-toggle is-index"
    assert field.children[1].n_clicks == 0
    assert field.children[2].children[0].data == ri
    mode = _callback(create_dash_app(), "_sync_material_field_mode")
    material = mode(1, "fused_silica", ri, "1.4")
    assert material == ("material-mode-toggle is-material", {"display": "none"}, {}, "fused_silica", ri)
    restored = mode(2, "fused_silica", "fused_silica", material[-1])
    assert restored == ("material-mode-toggle is-index", {}, {"display": "none"}, ri, ri)


def test_population_optical_fields_use_inline_scalar_validation():
    validate = _callback(create_dash_app(), "_validate_fields")
    ids = [{"section": "population", "name": name} for name in ("material", "medium")]
    classes, errors = validate(["1.5+0.01j", "1.33"], ids, None, None, None, None, None)
    assert classes == ["field-input", "field-input"] and errors == ["", ""]
    classes, errors = validate(["1.5,1.6", "1.33+0.01j"], ids, None, None, None, None, None)
    assert all("invalid" in class_name for class_name in classes)
    assert all(errors)
