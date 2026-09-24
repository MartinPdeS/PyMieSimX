"""Source, scatterer, and detector configuration cards."""

from dash import dcc, html

from PyMieSimX.gui.defaults import DEFAULT_WORKSPACE_SETTINGS
from PyMieSimX.gui.schemas import SECTION_FIELDS


def build_source_section():
    return _build_section("source-type", "source-fields", SECTION_FIELDS["source"], DEFAULT_WORKSPACE_SETTINGS["parameter_sweep"]["source_type"])


def build_scatterer_section():
    return _build_section("scatterer-type", "scatterer-fields", SECTION_FIELDS["scatterer"], DEFAULT_WORKSPACE_SETTINGS["parameter_sweep"]["scatterer_type"])


def build_detector_section():
    return _build_section("detector-type", "detector-fields", SECTION_FIELDS["detector"], DEFAULT_WORKSPACE_SETTINGS["parameter_sweep"]["detector_type"], detector=True)


def _build_section(selector_id, fields_id, choices, default, detector=False):
    options = [{"label": "No detector" if detector and key == "None" else key.replace("Set", ""), "value": key} for key in choices]
    persistence_key = "parameter-sweep-detector-default-v3" if detector else "parameter-sweep-defaults-v2"
    detector_alert = (
        html.Div(
            "A detector is required to compute coupling. Select a detector to enable it.",
            id="detector-coupling-alert",
            className="detector-coupling-alert",
        )
        if detector
        else None
    )
    return html.Div(
        id=f"{selector_id}-card",
        className="sidebar-section-body",
        children=[dcc.Dropdown(id=selector_id, className="dashboard-dropdown", options=options, value=default, clearable=False, searchable=False, optionHeight=38, maxHeight=200, persistence=persistence_key, persistence_type="session"), detector_alert, html.Div(id=fields_id, className="panel-body")],
    )
