#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pytest

from PyMieSim.units import ureg
import PyMieSimX.gui.services as services
from PyMieSimX.gui.parsing import MAX_EXPRESSION_POINTS, parse_material_values, parse_numeric_expression, parse_quantity_expression
from PyMieSimX.gui.services import (
    MAX_SWEEP_COMBINATIONS,
    ExperimentValidationError,
    available_measures,
    build_detector_set,
    build_figure,
    build_single_figure,
    estimate_sweep_size,
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
            return {component: np.ones((sampling, sampling), dtype=complex)}

    class FakeSetup:
        def get_representation(self, representation):
            assert representation == "nearfields"
            return FakeNearFields()

    monkeypatch.setattr(services, "build_single_setup", lambda **_: FakeSetup())

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
    assert summary["Scatterer"] == scatterer_type
