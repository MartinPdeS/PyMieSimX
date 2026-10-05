"""Simulation links preserve setup state and reject malformed configurations."""

import base64
import json
import zlib
from urllib.parse import urlencode, urlsplit

import pytest

from PyMieSimX.gui.interface import create_dash_app
from PyMieSimX.gui.layout import render_fields
from PyMieSimX.gui.sharing import (
    CAPTURE_CONTROLS, MAX_TOKEN_LENGTH, MAX_PAYLOAD_BYTES, control_key, encode_simulation, read_simulation, restore_controls,
)


def callback(app, name):
    for entry in app.callback_map.values():
        function = getattr(entry.get("callback"), "__wrapped__", None)
        if function and function.__name__ == name:
            return function
    raise AssertionError(name)


def components(component):
    if not hasattr(component, "to_plotly_json"):
        return
    yield component
    children = getattr(component, "children", [])
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from components(child)


def field_key(section, name):
    return control_key({"kind": "field", "section": section, "name": name})


def sweep_payload():
    return {"v": 1, "page": "/experiment", "controls": {
        "source-type": "PlaneWaveSet", "scatterer-type": "SphereSet", "detector-type": "None",
        "measure-select": ["Qsca", "Qext"], "x-axis-select": "diameter", "plot-experiment-projection": "cartesian",
        field_key("source", "wavelength"): "600:700:3", field_key("source", "polarization"): "0,90",
        field_key("source", "amplitude"): "1", field_key("scatterer", "diameter"): "80,120",
        field_key("scatterer", "material"): "1.45+0.02j", field_key("scatterer", "medium"): "1.33",
        "plot-experiment-font-size": 22, "plot-experiment-grid": False,
    }, "plot_settings": {"font_size": 22, "show_grid": False, "template": "plotly_dark", "graph_height": 640}}


def search_for(payload):
    return "?" + urlencode({"simulation": encode_simulation(payload)})


def test_round_trip_preserves_raw_sweeps_multiple_measures_and_plot_settings():
    payload = sweep_payload()
    assert read_simulation(search_for(payload), "/experiment") == payload
    assert read_simulation("?other=ordinary", "/experiment") is None


@pytest.mark.parametrize("search", ["?simulation=", "?simulation=!!!", "?simulation=e30", "?simulation=YQ&simulation=Yg",
                                    "?simulation=" + "a" * (MAX_TOKEN_LENGTH + 1)])
def test_invalid_link_is_rejected(search):
    with pytest.raises(ValueError):
        read_simulation(search, "/experiment")


@pytest.mark.parametrize("changes", [{"v": 2}, {"v": True}, {"controls": {"run-experiment-button": 1}},
                                     {"controls": {"source-type": ["PlaneWaveSet"]}},
                                     {"plot_settings": {"template": {"bad": "value"}}}])
def test_untrusted_payload_is_rejected(changes):
    payload = {**sweep_payload(), **changes}
    token = base64.urlsafe_b64encode(zlib.compress(json.dumps(payload).encode())).decode()
    with pytest.raises(ValueError):
        read_simulation("?simulation=" + token, "/experiment")


def test_wrong_workspace_and_oversized_configuration_are_rejected():
    with pytest.raises(ValueError, match="different workspace"):
        read_simulation(search_for(sweep_payload()), "/single")
    payload = sweep_payload()
    payload["controls"][field_key("source", "wavelength")] = "1," * MAX_PAYLOAD_BYTES
    with pytest.raises(ValueError, match="too large"):
        encode_simulation(payload)


@pytest.mark.parametrize("material", ["1.47+0.03j", "main/SiO2/Malitson", "gold"])
def test_material_mode_and_raw_input_restore_together(material):
    setup = sweep_payload()
    setup["controls"][field_key("scatterer", "material")] = material
    tree = restore_controls(render_fields("scatterer", "SphereSet"), setup)
    props = {control_key(item.id): item for item in components(tree) if hasattr(item, "id")}
    assert props[field_key("scatterer", "material")].value == material
    toggle = props[control_key({"kind": "material-toggle", "section": "scatterer", "name": "material"})]
    assert toggle.n_clicks == (1 if material.startswith("main/") else 0)
    for item in components(tree):
        if hasattr(item, "persistence"):
            assert item.persistence is False
    if material == "gold":
        store = props[control_key({"kind": "material-ri-value", "section": "scatterer", "name": "material"})]
        assert store.data == "gold"


def test_copy_callback_builds_portable_link_without_query_tokens_or_results():
    payload = sweep_payload()
    field_ids = [{"kind": "field", "section": "source", "name": "wavelength"}]
    inputs = [payload["controls"].get(name) for name in CAPTURE_CONTROLS]
    app = create_dash_app()
    copied = callback(app, "_copy_simulation_link")(
        1, "https://example.org/experiment?token=private#old", "/experiment",
        {"parameter_sweep": payload["plot_settings"]}, field_ids, ["600:700:3"], *inputs,
    )
    link = copied["url"]
    assert copied["clicks"] == 1
    assert "private" not in link
    assert urlsplit(link).fragment == ""
    restored = read_simulation(urlsplit(link).query, "/experiment")
    assert restored["controls"]["measure-select"] == ["Qsca", "Qext"]
    assert restored["controls"][field_key("source", "wavelength")] == "600:700:3"
    assert set(restored) == {"v", "page", "controls", "plot_settings"}


def test_route_restores_controls_and_arms_run_after_restoration():
    app = create_dash_app()
    page = callback(app, "_route_pages")("/experiment", search_for(sweep_payload()), 0, 0, 0, {}, {})[0]
    props = {item.id: item for item in components(page) if isinstance(getattr(item, "id", None), str)}
    assert props["measure-select"].value == ["Qsca", "Qext"]
    assert props["x-axis-select"].value == "diameter"
    assert props["x-axis-select"].options == [{"label": "diameter", "value": "diameter"}]
    assert props["plot-experiment-font-size"].value == 22
    assert props["run-experiment-button"].n_clicks == 0
    assert props["run-experiment-button"].disabled is False
    assert props["export-csv"].disabled is True
    armed = props["experiment-auto-run"].data
    assert armed["started"] is False
    assert armed["expected_controls"] == sweep_payload()["controls"]
    assert field_key("source", "wavelength") in armed["field_keys"]
    assert field_key("scatterer", "diameter") in armed["field_keys"]
    assert "runs automatically" in str(page)
    fields = callback(app, "_render_source_fields")("PlaneWaveSet", search_for(sweep_payload()))
    wavelength = next(item for item in components(fields) if getattr(item, "id", None) == {"kind": "field", "section": "source", "name": "wavelength"})
    assert wavelength.value == "600:700:3"
    invalid_page = callback(app, "_route_pages")("/experiment", "?simulation=invalid", 0, 0, 0, {}, {})[0]
    assert "could not be read" in str(invalid_page)
    assert next(item for item in components(invalid_page) if getattr(item, "id", None) == "experiment-auto-run").data is None


def test_compressed_payload_expansion_is_bounded():
    token = base64.urlsafe_b64encode(zlib.compress(b"a" * (MAX_PAYLOAD_BYTES + 1))).decode()
    with pytest.raises(ValueError, match="could not be read"):
        read_simulation("?simulation=" + token, "/experiment")


def test_shared_navigation_clears_previous_results():
    clear = callback(create_dash_app(), "_clear_results_for_shared_setup")
    assert clear(search_for(sweep_payload()), "/experiment") == (True, True)
    assert clear("", "/experiment") == (False, False)
    assert clear("?simulation=invalid", "/experiment") == (False, False)


def test_copy_reports_oversized_setup_without_claiming_success():
    key = {"kind": "field", "section": "source", "name": "wavelength"}
    copied = callback(create_dash_app(), "_copy_simulation_link")(
        1, "https://example.org/experiment", "/experiment", {}, [key], ["1," * MAX_PAYLOAD_BYTES],
        *[None for _ in CAPTURE_CONTROLS],
    )
    assert copied == {"clicks": 1, "url": None}
