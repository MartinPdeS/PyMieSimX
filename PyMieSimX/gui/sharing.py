"""Versioned, bounded simulation links independent of server job storage."""

import base64
import binascii
import json
import zlib
from math import isfinite
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from dash import ALL, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from PyMieSimX.gui.schemas import SECTION_FIELDS, SINGLE_SOURCE_FIELDS, SINGLE_SCATTERER_FIELDS, POPULATION_OPTICAL_FIELDS
from PyMieSimX.gui.parsing import is_numeric_material_value
from PyMieSimX.gui.material_catalog import material_dropdown_options
from PyMieSimX.gui.defaults import DEFAULT_WORKSPACE_SETTINGS

MAX_TOKEN_LENGTH = 3000
MAX_PAYLOAD_BYTES = 32000
WORKSPACES = {"/single": "particle_explorer", "/experiment": "parameter_sweep", "/population": "population"}
SECTION_SELECTORS = {
    "source": "source-type", "scatterer": "scatterer-type", "detector": "detector-type",
    "single-source": "single-source-type", "single-scatterer": "single-scatterer-type",
}
SCHEMAS = {**SECTION_FIELDS, "single-source": SINGLE_SOURCE_FIELDS, "single-scatterer": SINGLE_SCATTERER_FIELDS,
           "population": {"Sphere": POPULATION_OPTICAL_FIELDS}}
STATIC_CONTROLS = {
    "/single": ["single-source-type", "single-scatterer-type", "single-representation", "single-projection",
                "single-sampling", "single-nearfield-mode", "single-include-incident-field"],
    "/experiment": ["source-type", "scatterer-type", "detector-type", "measure-select", "x-axis-select", "plot-experiment-projection"],
    "/population": [f"population-{name}" for name in ("wavelength", "distribution", "diameter", "width", "minimum", "maximum", "sampling", "concentration-basis", "concentration")],
}
PLOT_CONTROLS = [f"plot-{prefix}-{name}" for prefix in ("single", "experiment")
                 for name in ("x-scale", "y-scale", "font-size", "line-width", "legend", "grid")]
CAPTURE_CONTROLS = list(dict.fromkeys([name for names in STATIC_CONTROLS.values() for name in names] + PLOT_CONTROLS))
RUN_BUTTONS = {"/single": "run-single-button", "/experiment": "run-experiment-button", "/population": "population-compute"}


def auto_run_config(setup):
    """Describe the restored state that must be mounted before starting a run."""
    path = setup["page"]
    controls = setup["controls"]
    sections = {"/single": ("single-source", "single-scatterer"),
                "/experiment": ("source", "scatterer", "detector"), "/population": ("population",)}[path]
    defaults = DEFAULT_WORKSPACE_SETTINGS.get(WORKSPACES[path], {})
    field_keys = []
    for section in sections:
        selector = SECTION_SELECTORS.get(section)
        model = controls.get(selector, defaults.get(section.removeprefix("single-") + "_type")) if selector else "Sphere"
        field_keys.extend(control_key({"kind": "field", "section": section, "name": spec.name}) for spec in SCHEMAS[section][model])
    return {"workspace": WORKSPACES[path], "control_names": CAPTURE_CONTROLS,
            "expected_controls": controls, "field_keys": field_keys,
            "plot_settings": setup.get("plot_settings", {}), "started": False}


def control_key(component_id):
    """Use stable keys for both string and Dash pattern IDs."""
    return json.dumps(component_id, sort_keys=True, separators=(",", ":")) if isinstance(component_id, dict) else component_id


def allowed_controls(path):
    sections = {"/single": ("single-source", "single-scatterer"), "/experiment": ("source", "scatterer", "detector"),
                "/population": ("population",)}[path]
    names = set(STATIC_CONTROLS[path])
    prefix = "single" if path == "/single" else "experiment"
    if path != "/population":
        names.update(name for name in PLOT_CONTROLS if name.startswith(f"plot-{prefix}-"))
    for section in sections:
        for specs in SCHEMAS[section].values():
            names.update(control_key({"kind": "field", "section": section, "name": spec.name}) for spec in specs)
    return names


def _finite_number(value):
    try:
        return isfinite(value)
    except (OverflowError, TypeError):
        return False


def _validate_payload(payload, path):
    if not isinstance(payload, dict) or type(payload.get("v")) is not int or payload.get("v") != 1:
        raise ValueError("This simulation link uses an unsupported format.")
    if path not in WORKSPACES or payload.get("page") != path:
        raise ValueError("This simulation link belongs to a different workspace.")
    if not set(payload).issubset({"v", "page", "controls", "plot_settings"}):
        raise ValueError("This simulation link contains unsupported settings.")
    controls = payload.get("controls")
    if not isinstance(controls, dict) or not set(controls).issubset(allowed_controls(path)):
        raise ValueError("This simulation link contains unsupported controls.")
    for value in controls.values():
        if isinstance(value, list):
            if len(value) > 100 or not all(isinstance(item, str) for item in value):
                raise ValueError("This simulation link contains invalid selections.")
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            raise ValueError("This simulation link contains invalid input values.")
        if isinstance(value, (int, float)) and not _finite_number(value):
            raise ValueError("This simulation link contains invalid input values.")
    for section, selector in SECTION_SELECTORS.items():
        if selector in controls and (not isinstance(controls[selector], str) or controls[selector] not in SCHEMAS[section]):
            raise ValueError("This simulation link selects an unsupported model.")
    list_controls = {"measure-select", "single-nearfield-mode", "single-include-incident-field"}
    for name, value in controls.items():
        if name in list_controls:
            if not isinstance(value, list):
                raise ValueError("This simulation link contains invalid selections.")
        elif isinstance(value, list):
            raise ValueError("This simulation link contains invalid input values.")
    settings = payload.get("plot_settings", {})
    if not isinstance(settings, dict):
        raise ValueError("This simulation link contains invalid plot settings.")
    numeric_settings = {"font_size": (8, 32), "line_width": (0.5, 8), "graph_height": (300, 1400)}
    enum_settings = {"template": {"match-theme", "plotly_white", "plotly_dark"},
                     "coordinate_system": {"cartesian", "polar"}, "x_scale": {"linear", "log"}}
    bool_settings = {"show_legend", "show_grid", "show_title", "log_y"}
    for name, value in settings.items():
        if name in numeric_settings:
            minimum, maximum = numeric_settings[name]
            valid = type(value) in (int, float) and _finite_number(value) and minimum <= value <= maximum
        elif name in enum_settings:
            valid = isinstance(value, str) and value in enum_settings[name]
        else:
            valid = name in bool_settings and isinstance(value, bool)
        if not valid:
            raise ValueError("This simulation link contains invalid plot settings.")
    for name in PLOT_CONTROLS:
        if name in controls:
            value = controls[name]
            suffix = name.split("-", 2)[2]
            if suffix in {"font-size", "line-width"}:
                minimum, maximum = numeric_settings[suffix.replace("-", "_")]
                valid = type(value) in (int, float) and _finite_number(value) and minimum <= value <= maximum
            elif suffix == "x-scale":
                valid = value in ("linear", "log")
            else:
                valid = isinstance(value, bool)
            if not valid:
                raise ValueError("This simulation link contains invalid plot controls.")
    enum_controls = {
        "single-representation": {"s1s2", "stokes", "stokes_q", "stokes_u", "stokes_v", "spf", "farfields",
                                  "nearfields", "nearfields_ex", "nearfields_ey", "nearfields_ez"},
        "single-projection": {"2d", "polar_1d", "3d", "3d_radial"},
        "plot-experiment-projection": {"cartesian", "polar"},
        "population-distribution": {"monodisperse", "lognormal", "gaussian", "uniform"},
        "population-concentration-basis": {"number", "volume"},
    }
    for name, choices in enum_controls.items():
        if name in controls and (not isinstance(controls[name], str) or controls[name] not in choices):
            raise ValueError("This simulation link contains unsupported selections.")
    if controls.get("x-axis-select") is not None:
        field_names = {spec.name for section in ("source", "scatterer", "detector")
                       for specs in SCHEMAS[section].values() for spec in specs}
        if controls["x-axis-select"] not in field_names:
            raise ValueError("This simulation link contains an unsupported axis.")
    for name, choice in (("single-nearfield-mode", "absolute"), ("single-include-incident-field", "include")):
        if name in controls and not set(controls[name]).issubset({choice}):
            raise ValueError("This simulation link contains unsupported selections.")
    if "measure-select" in controls:
        from PyMieSimX.gui.services import available_measures
        choices = available_measures(controls.get("scatterer-type", "SphereSet"), controls.get("detector-type", "None"))
        if not set(controls["measure-select"]).issubset(choices):
            raise ValueError("This simulation link contains unsupported measures.")
    return payload


def encode_simulation(payload):
    """Encode raw inputs without parsing away units or sweep notation."""
    _validate_payload(payload, payload.get("page"))
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError("This configuration is too large for a simulation link.")
    token = base64.urlsafe_b64encode(zlib.compress(raw)).decode().rstrip("=")
    if len(token) > MAX_TOKEN_LENGTH:
        raise ValueError("This configuration is too large for a simulation link.")
    return token


def read_simulation(search, path):
    """Return a validated shared setup, or None for an ordinary page visit."""
    parameters = parse_qs((search or "").lstrip("?"), keep_blank_values=True)
    if "simulation" not in parameters:
        return None
    tokens = parameters["simulation"]
    if len(tokens) != 1 or not tokens[0] or len(tokens[0]) > MAX_TOKEN_LENGTH:
        raise ValueError("This simulation link is invalid or too large.")
    token = tokens[0]
    try:
        raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(raw, MAX_PAYLOAD_BYTES + 1)
        if len(decoded) > MAX_PAYLOAD_BYTES or not decoder.eof or decoder.unused_data:
            raise ValueError("Invalid simulation payload size.")
        payload = json.loads(decoded)
    except (binascii.Error, ValueError, UnicodeDecodeError, RecursionError, zlib.error) as error:
        raise ValueError("This simulation link could not be read.") from error
    return _validate_payload(payload, path)


def shared_setup(search, path):
    """Let dependent callbacks render ordinary defaults after a malformed link."""
    try:
        return read_simulation(search, path)
    except ValueError:
        return None


def shared_plot_settings(settings, setup):
    if not setup or not setup.get("plot_settings"):
        return settings or {}
    key = WORKSPACES[setup["page"]]
    return {**(settings or {}), key: {**((settings or {}).get(key, {})), **setup["plot_settings"]}}


def restore_controls(component, setup):
    """Apply link values while preventing session persistence from overriding them."""
    if not setup:
        return component
    if isinstance(component, (list, tuple)):
        for child in component:
            restore_controls(child, setup)
        return component
    if not hasattr(component, "to_plotly_json"):
        return component
    props = component.to_plotly_json()["props"]
    component_id = props.get("id")
    controls = setup["controls"]
    key = control_key(component_id)
    if component_id == f"{setup['page'].strip('/')}-auto-run":
        component.data = auto_run_config(setup)
    if "persistence" in props:
        component.persistence = False
    if key in controls:
        component.value = controls[key]
        if component_id == "x-axis-select" and controls[key] is not None:
            # Dropdowns need a matching option on first mount, before dynamic
            # field callbacks discover all of the available sweep axes.
            component.options = [{"label": controls[key], "value": controls[key]}]
    if isinstance(component_id, dict) and component_id.get("kind") in {"material-toggle", "material-select", "material-ri-value"}:
        field_key = control_key({**component_id, "kind": "field"})
        value = controls.get(field_key)
        if value is not None:
            catalog_values = {option["value"] for option in material_dropdown_options(medium=component_id["name"] == "medium")}
            named = not is_numeric_material_value(str(value)) and value in catalog_values
            if component_id["kind"] == "material-toggle":
                component.n_clicks = 1 if named else 0
            elif component_id["kind"] == "material-select" and named:
                component.value = value
            elif component_id["kind"] == "material-ri-value" and not named:
                component.data = value
    restore_controls(props.get("children"), setup)
    return component


def sharing_controls(path):
    return html.Div(className="simulation-share-actions", children=[
        dcc.Store(id=f"{path.strip('/')}-auto-run", data=None),
        dcc.Store(id="simulation-link"),
        dcc.Store(id="simulation-copy-status"),
        html.Button([
            html.Span("Copy simulation link", className="simulation-copy-label"),
            html.Span("Copying…", className="simulation-copy-pending-label"),
            html.Span("✓ Copied", className="simulation-copy-success-label"),
            html.Span("Unable to copy", className="simulation-copy-error-label"),
        ], id="simulation-clipboard", n_clicks=0, title="Copy a link to this simulation setup",
            className="toolbar-button toolbar-button-secondary simulation-copy-button", **{"aria-live": "polite"}),
    ])


def register_sharing_callbacks(app):
    from dash import ClientsideFunction
    for path, button_id in RUN_BUTTONS.items():
        store_id = f"{path.strip('/')}-auto-run"
        app.clientside_callback(
            ClientsideFunction(namespace="simulation_sharing", function_name="auto_run"),
            Output(button_id, "n_clicks"), Output(store_id, "data"),
            Input(store_id, "data"),
            Input({"kind": "field", "section": ALL, "name": ALL}, "id"),
            Input({"kind": "field", "section": ALL, "name": ALL}, "value"),
            Input({"kind": "field", "section": ALL, "name": ALL}, "className"),
            Input("plot-settings-store", "data"),
            *[Input(name, "value", allow_optional=True) for name in CAPTURE_CONTROLS],
            State(button_id, "n_clicks"),
        )
    app.clientside_callback(
        ClientsideFunction(namespace="simulation_sharing", function_name="copy_link"),
        Output("simulation-copy-status", "data"), Input("simulation-link", "data"),
        prevent_initial_call=True,
    )
    app.clientside_callback(
        ClientsideFunction(namespace="simulation_sharing", function_name="copy_feedback"),
        Output("simulation-clipboard", "className"), Output("simulation-clipboard", "title"),
        Input("simulation-clipboard", "n_clicks"), Input("simulation-copy-status", "data"),
    )
    @app.callback(
        Output("experiment-result", "clear_data"), Output("single-result", "clear_data"),
        Input("url", "search"), State("url", "pathname"),
    )
    def _clear_results_for_shared_setup(search, path):
        clear = bool(shared_setup(search, path))
        return clear, clear

    @app.callback(
        Output("simulation-link", "data"),
        Input("simulation-clipboard", "n_clicks"),
        State("url", "href"), State("url", "pathname"), State("plot-settings-store", "data"),
        State({"kind": "field", "section": ALL, "name": ALL}, "id"),
        State({"kind": "field", "section": ALL, "name": ALL}, "value"),
        *[State(name, "value", allow_optional=True) for name in CAPTURE_CONTROLS],
        prevent_initial_call=True,
    )
    def _copy_simulation_link(clicks, href, path, settings, field_ids, field_values, *values):
        if not clicks or path not in WORKSPACES:
            raise PreventUpdate
        allowed = allowed_controls(path)
        controls = {name: value for name, value in zip(CAPTURE_CONTROLS, values) if name in allowed and value is not None}
        controls.update({control_key(field_id): value for field_id, value in zip(field_ids, field_values) if control_key(field_id) in allowed})
        plot = dict((settings or {}).get(WORKSPACES[path], {}))
        prefix = "single" if path == "/single" else "experiment"
        for name, key in (("x-scale", "x_scale"), ("y-scale", "log_y"), ("font-size", "font_size"),
                          ("line-width", "line_width"), ("legend", "show_legend"), ("grid", "show_grid")):
            if f"plot-{prefix}-{name}" in controls:
                plot[key] = controls[f"plot-{prefix}-{name}"]
        payload = {"v": 1, "page": path, "controls": controls, "plot_settings": plot}
        try:
            token = encode_simulation(payload)
        except ValueError:
            return {"clicks": clicks, "url": None}
        parts = urlsplit(href)
        link = urlunsplit((parts.scheme, parts.netloc, path, urlencode({"simulation": token}), ""))
        return {"clicks": clicks, "url": link}
