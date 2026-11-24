"""Every curated example links to a valid setup with real solver results."""

import json
from urllib.parse import urlsplit

import numpy as np
import pytest

from PyMieSimX.gui.experiment_service import run_experiment
from PyMieSimX.gui.interface import create_dash_app
from PyMieSimX.gui.pages.examples import EXAMPLES, build_examples_page, example_link
from PyMieSimX.gui.population_service import compute_population_optics
from PyMieSimX.gui.sharing import read_simulation
from PyMieSimX.gui.single_service import build_single_figure


def _raw_fields(controls, section):
    fields = {}
    for key, value in controls.items():
        if key.startswith("{"):
            field = json.loads(key)
            if field["section"] == section:
                fields[field["name"]] = value
    return fields


def test_examples_have_six_cards_and_an_active_route():
    page = build_examples_page()
    assert len(page.children[1].children) == 6
    assert len({example["id"] for example in EXAMPLES}) == 6
    app = create_dash_app()
    route = next(definition["callback"].__wrapped__ for definition in app.callback_map.values()
                 if definition.get("callback") and definition["callback"].__wrapped__.__name__ == "_route_pages")
    routed = route("/examples", "", 0, 0, 0, {}, {})
    assert routed[-3] == "sidebar-link active"
    assert routed[-2] == "sidebar-link"
    assert "Examples" in str(routed[0])


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda example: example["id"])
def test_example_links_restore_complete_setups_and_compute_finite_results(example):
    url = urlsplit(example_link(example))
    setup = read_simulation(url.query, url.path)
    assert setup == example["setup"]
    controls = setup["controls"]
    if setup["page"] == "/experiment":
        result = run_experiment(
            source_type=controls["source-type"], source_values=_raw_fields(controls, "source"),
            scatterer_type=controls["scatterer-type"], scatterer_values=_raw_fields(controls, "scatterer"),
            detector_type=controls["detector-type"], detector_values={}, measure=controls["measure-select"],
        )
        assert result["measures"] == controls["measure-select"]
        assert result["row_count"] > 100
        assert controls["x-axis-select"] in result["parameter_columns"]
        for measure in result["measures"]:
            assert np.isfinite([row[measure] for row in result["rows"]]).all()
        if example["id"] == "gold-nanoshell":
            assert len({row["shell_thickness"] for row in result["rows"]}) == 3
    elif setup["page"] == "/single":
        figure, _ = build_single_figure(
            source_type=controls["single-source-type"], source_values=_raw_fields(controls, "single-source"),
            scatterer_type=controls["single-scatterer-type"], scatterer_values=_raw_fields(controls, "single-scatterer"),
            representation=controls["single-representation"], sampling=int(controls["single-sampling"]),
            projection=controls["single-projection"], plot_settings=setup["plot_settings"],
        )
        assert figure.data
        assert all(np.isfinite(trace.r).all() for trace in figure.data)
    else:
        result = compute_population_optics(
            wavelength_nm=controls["population-wavelength"], **_raw_fields(controls, "population"),
            distribution=controls["population-distribution"], diameter_nm=controls["population-diameter"],
            width=controls["population-width"], minimum_nm=controls["population-minimum"],
            maximum_nm=controls["population-maximum"], sampling=controls["population-sampling"],
            concentration_basis=controls["population-concentration-basis"], concentration=controls["population-concentration"],
        )
        assert result["results"]
        assert all(row["value"] is None or np.isfinite(row["value"]) for row in result["results"])
        assert len(result["distribution"]["number_fractions"]) == 96
