#!/usr/bin/env python
# -*- coding: utf-8 -*-

from io import StringIO

import numpy as np
import pandas as pd
import pytest

from PyMieSim.units import ureg
import PyMieSimX.gui.computation as computation
from PyMieSimX.gui.material_catalog import material_dropdown_options
from PyMieSimX.gui.parsing import MAX_EXPRESSION_POINTS, parse_material_values, parse_numeric_expression, parse_quantity_expression
from PyMieSimX.gui.services import (
    MAX_SWEEP_COMBINATIONS,
    ExperimentValidationError,
    available_measures,
    build_detector_set,
    build_figure,
    build_single_figure,
    estimate_sweep_size,
    estimate_result_size,
    export_result_to_csv,
    run_experiment,
    validate_experiment_inputs,
)


def test_parse_quantity_expression_supports_ranges():
    quantity = parse_quantity_expression("400:800:5", ureg.nanometer)

    assert len(quantity) == 5
    assert quantity.units == ureg.nanometer
    assert np.isclose(quantity.magnitude[-1], 800)


def test_parse_quantity_expression_supports_linear_and_log_ranges():
    linear = parse_quantity_expression("lin:0:1:100", ureg.dimensionless)
    implicit_linear = parse_quantity_expression("0:1:100", ureg.dimensionless)
    logarithmic = parse_quantity_expression("log:1:1000:4", ureg.dimensionless)

    assert len(linear) == len(implicit_linear) == 100
    assert np.allclose(linear.magnitude, implicit_linear.magnitude)
    assert np.allclose(logarithmic.magnitude, [1, 10, 100, 1000])


def test_parse_expression_rejects_more_than_500_points():
    with pytest.raises(ValueError, match=str(MAX_EXPRESSION_POINTS)):
        parse_quantity_expression("0:1:501", ureg.nanometer)


def test_parse_material_values_supports_named_materials():
    material = parse_material_values("silver")

    assert material.__class__.__name__ == "TabulatedMaterial"


def test_material_options_follow_the_pymiesim_pyoptik_registry():
    material_options = material_dropdown_options()
    medium_options = material_dropdown_options(medium=True)
    material_values = {option["value"] for option in material_options}
    medium_values = {option["value"] for option in medium_options}

    assert material_options[0] == {"label": "Fused silica · Malitson", "value": "main/SiO2/Malitson"}
    assert {"specs/SCHOTT-optical/P-BK7", "main/Ag/Johnson", "main/Au/Olmon-ev"} <= material_values
    assert {"main/SiO2/Malitson", "main/H2O/Daimon-19.0C", "other/air/Ciddor"} <= medium_values
    assert {"main/Ag/Johnson", "main/Au/Olmon-ev"}.isdisjoint(medium_values)


def test_parse_material_values_supports_canonical_pyoptik_ids():
    material = parse_material_values("main/Ag/Johnson")

    assert material.__class__.__name__ == "TabulatedMaterial"


def test_parse_numeric_expression_supports_integer_scalars():
    sampling = parse_numeric_expression("200", integer=True)

    assert sampling == 200


def test_available_measures_excludes_coupling_without_detector():
    measures = available_measures("SphereSet", "None")

    assert "coupling" not in measures
    assert "Qsca" in measures


def test_build_detector_set_returns_none_for_detectorless_runs():
    detector = build_detector_set("None", {})

    assert detector is None


def _valid_experiment_values():
    return {
        "source_type": "GaussianSet",
        "source_values": {
            "wavelength": "650",
            "polarization": "0",
            "optical_power": "1e-3",
            "numerical_aperture": "0.2",
        },
        "scatterer_type": "SphereSet",
        "scatterer_values": {"diameter": "500", "material": "1.4", "medium": "1.0"},
        "detector_type": "PhotodiodeSet",
        "detector_values": {
            "numerical_aperture": "0.2",
            "gamma_offset": "0",
            "phi_offset": "0",
            "sampling": "50",
        },
        "measure": "Qsca",
    }


def test_validation_returns_field_specific_error_for_invalid_values():
    values = _valid_experiment_values()
    values["source_values"]["optical_power"] = "-1e-3"

    issues = validate_experiment_inputs(**values)

    assert any(issue.field == "optical_power" and "positive" in issue.message for issue in issues)


def test_sweep_size_is_limited_before_backend_execution():
    values = _valid_experiment_values()
    values["source_values"]["wavelength"] = "400:800:250"
    values["scatterer_values"]["diameter"] = "100:1000:250"

    estimate_values = {key: value for key, value in values.items() if key != "measure"}
    assert estimate_sweep_size(**estimate_values) == 62_500
    issues = validate_experiment_inputs(**values)
    assert any(issue.field == "sweep" and f"{MAX_SWEEP_COMBINATIONS:,}" in issue.message for issue in issues)

    with pytest.raises(ExperimentValidationError, match="62,500"):
        run_experiment(**values)


def test_export_and_plot_support_serialized_experiment_results():
    values = _valid_experiment_values()
    values["scatterer_values"]["diameter"] = "500:700:3"
    result = run_experiment(**values)

    csv = export_result_to_csv(result)
    figure = build_figure(result, x_axis="diameter")

    assert "Qsca" in csv
    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 3


def test_run_experiment_returns_serialized_dataframe():
    result = run_experiment(
        source_type="GaussianSet",
        source_values={
            "wavelength": "650",
            "polarization": "0",
            "optical_power": "1e-3",
            "numerical_aperture": "0.2",
        },
        scatterer_type="SphereSet",
        scatterer_values={
            "diameter": "500:700:3",
            "material": "1.4",
            "medium": "1.0",
        },
        detector_type="PhotodiodeSet",
        detector_values={
            "numerical_aperture": "0.2",
            "gamma_offset": "0",
            "phi_offset": "0",
            "sampling": "50",
        },
        measure="Qsca",
    )

    assert result["measure"] == "Qsca"
    assert result["row_count"] == 3
    assert len(result["rows"]) == 3
    assert result["parameter_columns"]


def test_single_representation_returns_plotly_traces():
    figure, summary = build_single_figure(
        source_type="Gaussian",
        source_values={},
        scatterer_type="Sphere",
        scatterer_values={},
        representation="s1s2",
        sampling=24,
    )

    assert len(figure.data) == 2
    assert len(figure.data[0].x) == 24
    assert summary["Representation"] == "S1S2"


def test_multiple_measures_share_one_backend_call_and_match_single_runs(monkeypatch):
    values = _valid_experiment_values()
    values["scatterer_values"].update(diameter="100,100,200", material="1.4+0.05j")
    values.update(detector_type="None", detector_values={}, measure=["Qsca", "Qabs", "Qext", "Qsca"])
    setup_class = computation.Setup
    calls = []

    class RecordingSetup:
        def __init__(self, **kwargs):
            self.setup = setup_class(**kwargs)

        def get(self, *measures, **kwargs):
            calls.append(measures)
            return self.setup.get(*measures, **kwargs)

    monkeypatch.setattr(computation, "Setup", RecordingSetup)
    result = run_experiment(**values)
    assert calls == [("Qsca", "Qabs", "Qext")]
    assert result["measure"] == "Qsca"
    assert result["measures"] == ["Qsca", "Qabs", "Qext"]
    assert result["parameter_columns"] == ["diameter"]
    assert result["row_count"] == 3
    frame = pd.DataFrame(result["rows"])
    assert np.allclose(frame.Qext, frame.Qsca + frame.Qabs)
    for measure in result["measures"]:
        single = run_experiment(**{**values, "measure": measure})
        assert np.allclose(frame[measure], [row[measure] for row in single["rows"]])
    csv_frame = pd.read_csv(StringIO(export_result_to_csv(result)))
    assert list(csv_frame.columns) == result["columns"]
    assert len(csv_frame) == 3
    assert np.allclose(csv_frame.Qext, frame.Qext)


@pytest.mark.parametrize("measures", [[], None, ["Qsca", "coupling"], ["Qsca", "unsupported"]])
def test_invalid_measure_selection_is_rejected_before_computation(monkeypatch, measures):
    def unexpected_setup(**kwargs):
        pytest.fail("Invalid selection must not construct a backend setup")

    monkeypatch.setattr(computation, "Setup", unexpected_setup)
    values = {**_valid_experiment_values(), "detector_type": "None", "detector_values": {}, "measure": measures}
    issues = validate_experiment_inputs(**values)
    assert any(issue.field == "measure" for issue in issues)
    with pytest.raises(ExperimentValidationError):
        run_experiment(**values)


def test_result_estimate_includes_all_measure_columns(monkeypatch):
    values = _valid_experiment_values()
    one = estimate_result_size(**values)
    three = estimate_result_size(**{**values, "measure": ["Qsca", "Qabs", "Qext"]})
    assert three.rows == one.rows
    assert three.columns == one.columns + 2
    assert three.estimated_bytes == one.estimated_bytes + 64 * one.rows
    monkeypatch.setattr(computation, "MAX_RESULT_PAYLOAD_BYTES", one.estimated_bytes)
    assert not validate_experiment_inputs(**values)
    assert any(issue.field == "result" for issue in validate_experiment_inputs(**{**values, "measure": ["Qsca", "Qabs", "Qext"]}))


def _multiple_measure_result():
    return {
        "measure": "Qsca", "measures": ["Qsca", "Qext", "Csca"],
        "rows": [{"diameter": 100, "Qsca": 1, "Qext": 2, "Csca": 1e-12}, {"diameter": 200, "Qsca": 2, "Qext": 3, "Csca": 2e-12}],
        "columns": ["diameter", "Qsca", "Qext", "Csca"], "parameter_columns": ["diameter"],
        "units": {"diameter": "nanometer", "Qsca": "dimensionless", "Qext": "dimensionless", "Csca": "meter ** 2"}, "row_count": 2,
    }


def test_multiple_measure_plot_overlays_comparable_units_and_separates_others():
    figure = build_figure(_multiple_measure_result(), "diameter", plot_settings={"x_scale": "log", "log_y": True}, theme="dark")
    assert [trace.name for trace in figure.data] == ["Qsca", "Qext", "Csca"]
    assert [trace.yaxis for trace in figure.data] == ["y", "y", "y2"]
    assert len({trace.line.color for trace in figure.data}) == 3
    assert figure.layout.xaxis.matches == "x2"
    assert figure.layout.xaxis.type == figure.layout.xaxis2.type == "log"
    assert figure.layout.yaxis.type == figure.layout.yaxis2.type == "log"
    assert figure.layout.yaxis.title.text == "Value"
    assert figure.layout.yaxis2.title.text == "Value [m²]"
    assert figure.layout.meta["measures"] == ["Qsca", "Qext", "Csca"]


def test_multiple_measure_plot_preserves_parameter_series():
    result = _multiple_measure_result()
    result["parameter_columns"].append("wavelength")
    for index, row in enumerate(result["rows"]):
        row["wavelength"] = 600 + index * 50
    figure = build_figure(result, "diameter")
    assert len(figure.data) == 6
    assert all(trace.name.startswith(trace.legendgroup + " | ") for trace in figure.data)
    assert "wavelength" in figure.layout.meta["legend_description"]


@pytest.mark.parametrize("projection, settings", [("polar", {}), ("cartesian", {"coordinate_system": "polar"})])
def test_multiple_measure_polar_plot_preserves_units_and_panels(projection, settings):
    result = _multiple_measure_result()
    result["units"]["diameter"] = "radian"
    for row, angle in zip(result["rows"], (0, np.pi)):
        row["diameter"] = angle
    figure = build_figure(result, "diameter", projection=projection, plot_settings=settings)
    assert [trace.type for trace in figure.data] == ["scatterpolar"] * 3
    assert [trace.subplot for trace in figure.data] == ["polar", "polar", "polar2"]
    assert np.allclose(figure.data[0].theta, [0, 180])
    assert figure.layout.polar.domain.y[0] > figure.layout.polar2.domain.y[1]


def test_multiple_measures_with_single_parameter_combination_plot_as_bars():
    values = {**_valid_experiment_values(), "measure": ["Qsca", "Qabs"]}
    result = run_experiment(**values)
    figure = build_figure(result, None)
    assert result["row_count"] == 1
    assert result["parameter_columns"] == []
    assert [trace.type for trace in figure.data] == ["bar", "bar"]
    assert [trace.name for trace in figure.data] == ["Qsca", "Qabs"]


@pytest.mark.parametrize(
    ("scatterer_type", "scatterer_values"),
    [
        ("InfiniteCylinder", {"diameter": "200", "material": "1.4", "medium": "1.0"}),
        (
            "CoreShell",
            {
                "core_diameter": "120",
                "shell_thickness": "40",
                "core_material": "1.4",
                "shell_material": "1.5",
                "medium": "1.0",
            },
        ),
    ],
)
def test_single_nearfield_supports_new_scatterer_types(monkeypatch, scatterer_type, scatterer_values):
    class FakeNearFields:
        u = np.linspace(-1, 1, 24) * ureg.nanometer
        v = np.linspace(-1, 1, 24) * ureg.nanometer

        def compute(self, component, *, type, sampling):
            assert component == "Ex"
            assert type == "total"
            assert sampling == 24
            # An asymmetric field catches accidental swaps of the plane axes.
            return {component: np.arange(sampling * sampling).reshape(sampling, sampling).astype(complex)}

    class FakeSetup:
        def get_representation(self, representation):
            assert representation == "nearfields"
            return FakeNearFields()

    monkeypatch.setattr(computation, "build_single_setup", lambda **_: FakeSetup())

    figure, summary = build_single_figure(
        source_type="PlaneWave",
        source_values={},
        scatterer_type=scatterer_type,
        scatterer_values=scatterer_values,
        representation="nearfields_ex",
        sampling=24,
    )

    assert len(figure.data) == 1
    assert len(figure.data[0].z) == 24
    np.testing.assert_array_equal(figure.data[0].z, np.arange(24 * 24).reshape(24, 24).T)
    assert summary["Scatterer"] == scatterer_type
