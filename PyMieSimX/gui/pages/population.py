"""Ensemble Optics page and its focused Dash callbacks."""

import logging

from dash import Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import numpy as np

from PyMieSimX.gui.components import Card
from PyMieSimX.gui.layout import build_tabbed_sidebar, render_field
from PyMieSimX.gui.material_catalog import material_dropdown_options
from PyMieSimX.gui.schemas import POPULATION_OPTICAL_FIELDS
from PyMieSimX.gui.population_service import (
    build_population_distribution, compute_population_optics, export_population_to_csv,
)

LOGGER = logging.getLogger(__name__)
FIELDS = ("wavelength", "material", "medium", "distribution", "diameter", "width", "minimum", "maximum",
          "sampling", "concentration-basis", "concentration")


def _control_id(name):
    """Keep optical inputs on the shared material renderer and MATCH callbacks."""
    if name in {"material", "medium"}:
        return {"kind": "field", "section": "population", "name": name}
    return f"population-{name}"


def _field(name, label, value, *, options=None, help_text=None):
    control = dcc.Dropdown(
        id=f"population-{name}", options=options, value=value, clearable=False,
        searchable=False, className="dashboard-dropdown",
    ) if options else dcc.Input(id=f"population-{name}", value=value, type="text", debounce=True, className="field-input")
    return html.Div(id=f"population-{name}-field", className="field-block", children=[
        html.Label(label, id=f"population-{name}-label", htmlFor=f"population-{name}"), control,
        html.Small(help_text) if help_text else None,
    ])


def _panel(title, children, color="blue"):
    return html.Section(className=Card.classes(color=color, extra="panel"), children=[
        html.Div(className="card-header panel-header", children=html.H2(title)),
        html.Div(className="card-body", children=children),
    ])


def _sidebar_section(title, children, color):
    """Use the same section body and heading treatment as the other workspaces."""
    return html.Div(className="sidebar-section-body", children=[
        html.Div(className=f"sidebar-type-selector sidebar-type-selector--{color}",
                 children=html.H2(title, className="sidebar-type-label")),
        html.Div(className="panel-body", children=children),
    ])


def _compute_label(text):
    return [html.Span("▶", className="toolbar-button-icon", **{"aria-hidden": "true"}), text]


def build_population_page():
    """Build the population workspace with shared collapsible side panels."""
    particle_fields = _sidebar_section("Particle properties", [
        _field("wavelength", "Vacuum wavelength [nm]", "650"),
        *[html.Div(id=f"population-{field.name}-field", children=render_field("population", field))
          for field in POPULATION_OPTICAL_FIELDS],
    ], "blue")
    distribution_fields = _sidebar_section("Size distribution", [
        _field("distribution", "Number-based distribution", "lognormal", options=[
            {"label": label, "value": value} for label, value in (
                ("Monodisperse", "monodisperse"), ("Gaussian (truncated)", "gaussian"),
                ("Lognormal", "lognormal"), ("Uniform", "uniform"))]),
        _field("diameter", "Geometric median diameter [nm]", "500"),
        _field("width", "Geometric standard deviation", "1.2"),
        _field("minimum", "Minimum diameter [nm]", "100"),
        _field("maximum", "Maximum diameter [nm]", "1000"),
        _field("sampling", "Distribution sampling points", "128", help_text="16–128 points. Increase sampling to check numerical convergence."),
    ], "yellow")
    concentration_fields = _sidebar_section("Concentration", [
        _field("concentration-basis", "Concentration basis", "number", options=[
            {"label": "Number concentration", "value": "number"},
            {"label": "Particle volume fraction", "value": "volume"}]),
        _field("concentration", "Number concentration [particles/mL]", "1e9"),
    ], "cyan")
    model_notes = _sidebar_section("Model and averaging", [
        html.P("Homogeneous spheres under plane-wave illumination, using independent scattering. Particle interactions and multiple scattering are excluded; use dilute populations."),
        html.P("mu_a includes particle absorption only. Host-medium absorption is excluded."),
        html.P("Cross sections and number efficiencies are number averages. Area efficiencies are mean cross section divided by mean projected area. Effective g is weighted by scattering cross section."),
        html.P("Population albedo = mean Csca / mean Cext. Albedo and g are shown as undefined when extinction or scattering is zero; albedo describes the particles even at zero concentration."),
    ], "purple")
    return html.Div(className="page-content-stack population-page", children=[
        dcc.Store(id="population-result"), dcc.Download(id="population-download"),
        dcc.Store(id="population-right-sidebar-active", data=None),
        html.Section(className="page-hero", children=[
            html.P("From particles to population properties", className="eyebrow"),
            html.P("Define particle properties, size distribution, and concentration in the side panels, then compute all optical properties at one wavelength.", className="hero-text"),
        ]),
        html.Section(className="population-workspace", children=[
            html.Div(className="result-column population-output", children=[
                html.Div(className="graph-toolbar", children=[
                    html.Button(_compute_label("Compute"), id="population-compute", n_clicks=0,
                                className="toolbar-button toolbar-button-primary"),
                    html.Button([html.Span("⤓", className="toolbar-button-icon", **{"aria-hidden": "true"}), "Export CSV"],
                                id="population-export", disabled=True, className="toolbar-button toolbar-button-secondary"),
                ]),
                html.Div(id="population-status", role="status", children="Ready. Click Compute to calculate all properties."),
                _panel("Distribution preview", [
                    dcc.Graph(id="population-preview", config={"displaylogo": False}),
                    html.Div(id="population-preview-error", role="status"),
                    html.P("The preview shows discrete number fractions used for integration. Gaussian distributions are truncated and renormalized within the diameter bounds. The initial view focuses on the central 99.9% of number fractions; zoom out to inspect tails."),
                ], "green"),
                _panel("Population properties", [dcc.Loading(html.Div(id="population-results"))]),
            ]),
        ]),
        build_tabbed_sidebar("population-right-sidebar", [
            {"tab_id": "population-tab-particle", "panel_id": "population-panel-particle", "label": "Particle", "color": "blue", "content": particle_fields, "active": False},
            {"tab_id": "population-tab-distribution", "panel_id": "population-panel-distribution", "label": "Distribution", "color": "yellow", "content": distribution_fields, "active": False},
            {"tab_id": "population-tab-concentration", "panel_id": "population-panel-concentration", "label": "Concentration", "color": "cyan", "content": concentration_fields, "active": False},
            {"tab_id": "population-tab-model", "panel_id": "population-panel-model", "label": "Model", "color": "purple", "content": model_notes, "active": False},
        ]),
    ])

def _result_table(result):
    return html.Table(className="documentation-table", children=[
        html.Thead(html.Tr([html.Th("Property"), html.Th("Value"), html.Th("Unit")])),
        html.Tbody([html.Tr(title=row["definition"], children=[
            html.Td(row["parameter"]), html.Td("Undefined" if row["value"] is None else f'{row["value"]:.6g}'),
            html.Td(row["unit"]),
        ]) for row in result["results"]]),
    ])


def register_population_callbacks(app):
    """Register preview, computation, invalidation, and export independently of sweep jobs."""
    @app.callback(
        Output("population-diameter-label", "children"), Output("population-width-label", "children"),
        Output("population-diameter-field", "style"), Output("population-width-field", "style"),
        Output("population-minimum-field", "style"), Output("population-maximum-field", "style"),
        Output("population-sampling-field", "style"), Output("population-width", "value"),
        Input("population-distribution", "value"),
    )
    def _population_distribution_controls(distribution):
        hidden = {"display": "none"}
        diameter_label = {"monodisperse": "Diameter [nm]", "gaussian": "Gaussian mean diameter [nm]"}.get(distribution, "Geometric median diameter [nm]")
        return (diameter_label, "Standard deviation [nm]" if distribution == "gaussian" else "Geometric standard deviation",
                hidden if distribution == "uniform" else {}, {} if distribution in {"gaussian", "lognormal"} else hidden,
                {} if distribution in {"gaussian", "uniform"} else hidden,
                {} if distribution in {"gaussian", "uniform"} else hidden,
                hidden if distribution == "monodisperse" else {}, "50" if distribution == "gaussian" else "1.2")

    @app.callback(Output("population-concentration-label", "children"), Output("population-concentration", "value"),
                  Input("population-concentration-basis", "value"))
    def _population_concentration_controls(basis):
        return ("Particle volume fraction [0–1]", "0.001") if basis == "volume" else ("Number concentration [particles/mL]", "1e9")

    @app.callback(Output("population-preview", "figure"), Output("population-preview-error", "children"),
                  *[Input(f"population-{name}", "value") for name in ("distribution", "diameter", "width", "minimum", "maximum", "sampling")],
                  Input("theme-store", "data"))
    def _population_preview(distribution, diameter, width, minimum, maximum, sampling, theme):
        figure = go.Figure()
        figure.update_layout(template="plotly_dark" if (theme or {}).get("theme") == "dark" else "plotly_white",
                              margin={"l": 55, "r": 15, "t": 20, "b": 55}, height=300,
                              xaxis_title="Diameter [nm]", yaxis_title="Number fraction", paper_bgcolor="rgba(0,0,0,0)")
        try:
            particles = build_population_distribution(distribution=distribution, diameter_nm=diameter, width=width,
                                                      minimum_nm=minimum, maximum_nm=maximum, sampling=sampling)
            diameters = np.asarray(particles.diameters.to("nm").magnitude)
            weights = np.asarray(particles.number_fractions)
            cumulative = np.cumsum(weights)
            lower = diameters[min(np.searchsorted(cumulative, 0.0005), len(diameters)-1)]
            upper = diameters[min(np.searchsorted(cumulative, 0.9995), len(diameters)-1)]
            padding = max((upper-lower) * 0.1, float(lower) * 0.05)
            bar_width = np.gradient(diameters) * 0.8 if len(diameters) > 1 else [float(lower) * 0.08]
            figure.add_trace(go.Bar(x=diameters, y=weights, width=bar_width,
                                    name="Number fraction", marker_color="#4c86d9"))
            figure.update_xaxes(range=[max(0, lower-padding), upper+padding])
            return figure, ""
        except (ValueError, TypeError, RuntimeError) as error:
            return figure, str(error)

    @app.callback(Output("population-result", "data"), Output("population-results", "children"),
                  Output("population-status", "children"), Output("population-export", "disabled"),
                  Input("population-compute", "n_clicks"), *[State(_control_id(name), "value") for name in FIELDS],
                  prevent_initial_call=True, running=[
                      (Output("population-compute", "disabled"), True, False),
                      (Output("population-compute", "children"), _compute_label("Computing…"), _compute_label("Compute")),
                      *[(Output(_control_id(name), "disabled"), True, False) for name in FIELDS],
                      *[(Output({"kind": kind, "section": "population", "name": name}, "disabled"),
                         True, not material_dropdown_options(medium=name == "medium"))
                        for name in ("material", "medium") for kind in ("material-toggle", "material-select")],
                  ])
    def _compute_population(clicks, wavelength, material, medium, distribution, diameter, width, minimum, maximum, sampling, basis, concentration):
        if not clicks:
            raise PreventUpdate
        try:
            result = compute_population_optics(
                wavelength_nm=wavelength, material=material, medium=medium, distribution=distribution,
                diameter_nm=diameter, width=width, minimum_nm=minimum, maximum_nm=maximum, sampling=sampling,
                concentration_basis=basis, concentration=concentration,
            )
            return result, _result_table(result), "Completed. All population properties are shown below.", False
        except (ValueError, TypeError, RuntimeError) as error:
            return None, [], f"Unable to compute: {error}", True
        except Exception:
            LOGGER.exception("Population computation failed")
            return None, [], "Computation failed. Check your inputs and try again.", True

    @app.callback(Output("population-result", "data", allow_duplicate=True),
                  Output("population-results", "children", allow_duplicate=True),
                  Output("population-status", "children", allow_duplicate=True),
                  Output("population-export", "disabled", allow_duplicate=True),
                  *[Input(_control_id(name), "value") for name in FIELDS], prevent_initial_call=True)
    def _invalidate_population(*values):
        return None, [], "Ready. Click Compute to calculate all properties.", True

    @app.callback(Output("population-download", "data"), Input("population-export", "n_clicks"),
                  State("population-result", "data"), prevent_initial_call=True)
    def _export_population(clicks, result):
        if not clicks or not result:
            return no_update
        return dcc.send_string(export_population_to_csv(result), "ensemble-optics.csv")
