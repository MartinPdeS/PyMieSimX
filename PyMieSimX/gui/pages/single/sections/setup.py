"""Source and scatterer setup section."""

from dash import dcc, html

from PyMieSimX.gui.defaults import DEFAULT_WORKSPACE_SETTINGS
from PyMieSimX.gui.schemas import SINGLE_SCATTERER_FIELDS, SINGLE_SOURCE_FIELDS


def build_source_section():
    return _setup_card("single-source-type", "single-source-fields", SINGLE_SOURCE_FIELDS, DEFAULT_WORKSPACE_SETTINGS["particle_explorer"]["source_type"])


def build_scatterer_section():
    return _setup_card("single-scatterer-type", "single-scatterer-fields", SINGLE_SCATTERER_FIELDS, DEFAULT_WORKSPACE_SETTINGS["particle_explorer"]["scatterer_type"])


def _setup_card(selector_id, fields_id, choices, default):
    return html.Div(
        id=f"{selector_id}-card",
        className="sidebar-section-body",
        children=[dcc.Dropdown(id=selector_id, className="dashboard-dropdown", options=[{"label": key, "value": key} for key in choices], value=default, clearable=False, searchable=False, optionHeight=38, maxHeight=200, persistence="particle-explorer-defaults-v3", persistence_type="session"), html.Div(id=fields_id, className="panel-body")],
    )
