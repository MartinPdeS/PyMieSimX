"""Home page composition."""

from importlib.metadata import PackageNotFoundError, version
from math import isfinite

from dash import dcc, html
import numpy as np
import plotly.graph_objects as go

from PyMieSimX.gui.components import Card
from PyMieSimX.gui.usage_metrics import show_public_metrics

def build_home_page(*, home_visits: int | float | None = None):
    """Build the landing page and its workflow cards."""
    return html.Div(
        className="page-content-stack",
        children=[
            html.Div(
                [
                    html.Span("Version:", className="version-widget-label"),
                    html.Span(_package_version(), className="version-widget-value"),
                ],
                className="version-widget",
            ),
            html.Section(
                className="page-hero home-page-hero",
                children=[
                    html.Div(
                        [
                            html.H1("PyMieSim"),
                            html.P(
                                "An open-source library for fast and flexible far-field Mie scattering simulations.",
                                className="hero-text",
                            ),
                        ],
                        className="home-hero-copy",
                    ),
                    html.Div(
                        [
                            _visit_metric(home_visits),
                            html.Div(
                                [
                                    html.A(
                                        [
                                            html.Span("♥", className="home-support-icon", **{"aria-hidden": "true"}),
                                            html.Span("Support Developer", className="home-support-label"),
                                            html.Span("↗", className="home-support-arrow", **{"aria-hidden": "true"}),
                                        ],
                                        id="home-support-developer",
                                        href="https://github.com/sponsors/MartinPdeS",
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        className="home-support-button",
                                    ),
                                    html.A(
                                        [
                                            html.Span("☆", className="home-support-icon", **{"aria-hidden": "true"}),
                                            html.Span("Star PyMieSim on GitHub", className="home-support-label"),
                                            html.Span("↗", className="home-support-arrow", **{"aria-hidden": "true"}),
                                        ],
                                        id="home-star-repository",
                                        href="https://github.com/MartinPdeS/PyMieSim",
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        className="home-support-button home-star-button",
                                    ),
                                ],
                                className="home-support-actions",
                            ),
                        ],
                        className="home-hero-actions",
                    ),
                ],
            ),
            html.Div(
                className="home-capability-grid",
                children=[
                    _capability_card(
                        "Single Scatterer",
                        "Inspect one optical setup through angular scattering, polarization, phase functions, and field representations.",
                        ["Configure source", "Configure scatterer", "Render representations"],
                        "Open Single Scatterer",
                        "/single",
                        html.Img(src="/assets/home-spf-radial.gif", className="home-capability-preview home-capability-preview-image", alt="Rotating scattering phase function 3D radial surface"),
                        "Scattering phase function — rotating 3D radial surface",
                        "purple",
                    ),
                    _capability_card(
                        "Parameter Scan",
                        "Run source, scatterer, and detector configurations across parameter sweeps and export structured results for analysis.",
                        ["Configure source", "Configure scatterer and detector", "Run and export results"],
                        "Open Parameter Scan",
                        "/experiment",
                        _qsca_preview(),
                        "Scattering-efficiency sweep",
                        "green",
                    ),
                    _capability_card(
                        "Ensemble Optics",
                        "Turn a particle size distribution and concentration into scattering, absorption, albedo, and averaged optical properties at one wavelength.",
                        ["Define particle properties", "Choose a distribution and concentration", "Compute all properties and export"],
                        "Open Ensemble Optics",
                        "/population",
                        _distribution_preview(),
                        "Gaussian and lognormal size distributions",
                        "blue",
                    ),
                ],
            ),
        ],
    )

def _visit_metric(home_visits: int | float | None):
    """Show an available server count without displaying local or failed metrics."""
    if not show_public_metrics() or home_visits is None or not isfinite(home_visits) or home_visits < 0:
        return None
    return html.Div(
        [
            html.Strong(f"{int(home_visits):,}", id="home-public-visit-count", className="home-visit-value"),
            html.Span("Webapp visits", className="home-visit-label"),
        ],
        className="home-visit-metric",
    )


def _package_version() -> str:
    try:
        return version("PyMieSimX")
    except PackageNotFoundError:
        return "development"


def _capability_card(
    title: str,
    description: str,
    steps: list[str],
    button_text: str,
    href: str,
    preview: go.Figure | html.Img,
    preview_title: str,
    color: str,
):
    preview_content = preview if isinstance(preview, html.Img) else dcc.Graph(
        figure=preview,
        config={"displayModeBar": False, "staticPlot": True, "responsive": True},
        className="home-capability-preview",
    )
    return html.Section(
        id=f"home-workflow-{href.strip('/')}",
        className=Card.classes(color=color, extra="home-capability-card"),
        children=[
            html.Div(title, className="home-section-header"),
            html.Div(
                className="home-capability-body",
                children=[
                    html.Div(
                        className="home-capability-content",
                        children=[
                            html.Div(
                                className="home-capability-copy",
                                children=[
                                    html.P(description),
                                    html.Div(
                                        [html.Div([html.Span(str(index), className="home-step-number"), html.Span(step)]) for index, step in enumerate(steps, start=1)],
                                        className="home-step-list",
                                    ),
                                    html.A(button_text, href=href, className="home-workflow-button"),
                                ],
                            ),
                            html.Div(
                                className="home-preview-panel",
                                children=[
                                    html.Div(preview_title, className="home-preview-title"),
                                    preview_content,
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def _preview_layout(figure: go.Figure, *, x_title: str = "", y_title: str = "") -> go.Figure:
    figure.update_layout(
        template="plotly_white",
        height=220,
        margin={"l": 48, "r": 16, "t": 12, "b": 42},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font={"size": 11, "color": "#52697a"},
        xaxis={"title": x_title, "showgrid": False, "zeroline": False},
        yaxis={"title": y_title, "gridcolor": "rgba(82,105,122,.14)", "zeroline": False},
    )
    return figure


def _qsca_preview() -> go.Figure:
    """Build an illustrative scattering-efficiency sweep preview."""
    diameter = np.linspace(80.0, 1000.0, 180)
    envelope = 2.0 * (1.0 - np.exp(-diameter / 260.0))
    low_index_qsca = np.clip(
        envelope + 0.34 * np.sin(diameter / 62.0) * np.exp(-diameter / 920.0),
        0.0,
        None,
    )
    high_index_qsca = np.clip(
        1.08 * envelope + 0.62 * np.sin(diameter / 49.0) * np.exp(-diameter / 820.0),
        0.0,
        None,
    )
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=diameter,
            y=low_index_qsca,
            mode="lines",
            line={"color": "#2672d6", "width": 3},
            name="n = 1.45",
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=diameter,
            y=high_index_qsca,
            mode="lines",
            line={"color": "#1c7c54", "width": 3},
            name="n = 1.59",
            hoverinfo="skip",
        )
    )
    figure = _preview_layout(figure, x_title="Diameter (nm)", y_title="Qsca")
    figure.update_layout(
        showlegend=True,
        legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": 1.13, "font": {"size": 10}},
        margin={"t": 32},
    )
    return figure


def _distribution_preview() -> go.Figure:
    """Illustrate Gaussian and lognormal particle-size probability densities."""
    diameter = np.linspace(100, 1000, 240)
    sigma_log = np.log(1.3)
    lognormal = np.exp(-0.5 * (np.log(diameter / 450) / sigma_log) ** 2) / (diameter * sigma_log * np.sqrt(2 * np.pi))
    gaussian = np.exp(-0.5 * ((diameter - 520) / 80) ** 2) / (80 * np.sqrt(2 * np.pi))
    figure = go.Figure([
        go.Scatter(x=diameter, y=lognormal, mode="lines", name="Lognormal", hoverinfo="skip",
                   line={"color": "#2672d6", "width": 3}, fill="tozeroy", fillcolor="rgba(38,114,214,.15)"),
        go.Scatter(x=diameter, y=gaussian, mode="lines", name="Gaussian", hoverinfo="skip",
                   line={"color": "#b47b1d", "width": 3, "dash": "dot"}),
    ])
    figure = _preview_layout(figure, x_title="Diameter (nm)", y_title="Probability density (nm⁻¹)")
    figure.update_layout(showlegend=True, margin={"t": 32},
                         legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": 1.13, "font": {"size": 10}})
    return figure
