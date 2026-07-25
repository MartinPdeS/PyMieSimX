"""Sellmeier model documentation page."""

from dash import html

from PyMieSimX.gui.components import Card
from PyMieSimX.gui.material_catalog import load_material_catalog


def build_sellmeier_page():
    """Build the Sellmeier reference page used by material input workflows."""
    catalog = load_material_catalog()
    sellmeier = catalog.get("sellmeier_reference", [])
    if isinstance(sellmeier, dict):
        sellmeier = [sellmeier]

    parameter_rows = [
        html.Tr(
            [
                html.Td(str(row.get("material", ""))),
                html.Td(str(row.get("B1", "—"))),
                html.Td(str(row.get("B2", "—"))),
                html.Td(str(row.get("B3", "—"))),
                html.Td(str(row.get("C1_um2", "—"))),
                html.Td(str(row.get("C2_um2", "—"))),
                html.Td(str(row.get("C3_um2", "—"))),
            ]
        )
        for row in sellmeier
        if isinstance(row, dict)
    ]

    return html.Div(
        className="page-content-stack documentation-page",
        children=[
            html.Section(
                className="page-hero documentation-page-hero",
                children=[
                    html.P("PyMieSim material model", className="eyebrow"),
                    html.H1("Sellmeier Relation"),
                    html.P(
                        "Use this page as a quick reference when selecting or validating dispersive dielectric materials.",
                        className="hero-text",
                    ),
                ],
            ),
            html.Section(
                className=Card.classes(color="blue", extra="panel documentation-detail-card"),
                children=[
                    html.Div(className="card-header panel-header", children=[html.H2("Equation")]),
                    html.Div(
                        className="card-body",
                        children=[
                            html.P("Sellmeier form used for refractive index dispersion:"),
                            html.Div(
                                className="documentation-equation",
                                children="n(lambda)^2 = 1 + B1*lambda^2/(lambda^2 - C1) + B2*lambda^2/(lambda^2 - C2) + B3*lambda^2/(lambda^2 - C3)",
                            ),
                            html.P("lambda is in micrometers (um). Coefficients C1, C2, C3 are in um^2."),
                        ],
                    ),
                ],
            ),
            html.Section(
                className=Card.classes(color="green", extra="panel documentation-detail-card"),
                children=[
                    html.Div(className="card-header panel-header", children=[html.H2("Parameter Table")]),
                    html.Div(
                        className="card-body",
                        children=[
                            html.P("Reference coefficients used for Sellmeier evaluation:"),
                            html.Table(
                                className="documentation-table",
                                children=[
                                    html.Thead(html.Tr([html.Th("Material"), html.Th("B1"), html.Th("B2"), html.Th("B3"), html.Th("C1 (um^2)"), html.Th("C2 (um^2)"), html.Th("C3 (um^2)")])),
                                    html.Tbody(parameter_rows),
                                ],
                            ),
                            html.P(
                                "An em dash means that the source material model does not provide that B/C term. "
                                "For example, soda_lime_glass uses Formula 5 instead of the three-term Sellmeier form:",
                                className="documentation-callout",
                            ),
                            html.Div(
                                "n(lambda)^2 = (1.5130 - 0.003169*lambda^2 + 0.003962*lambda^4) / (1 - 2*lambda^2)",
                                className="documentation-equation documentation-equation-compact",
                            ),
                            html.P("You can still use the RI toggle for direct n or n+ik entry when dispersion is not required.", className="documentation-callout"),
                        ],
                    ),
                ],
            ),
            html.Section(
                className=Card.classes(color="blue", extra="panel documentation-note"),
                children=[
                    html.Div(className="card-header panel-header", children=[html.H2("Navigation")]),
                    html.Div(
                        className="card-body documentation-note-body",
                        children=[
                            html.P("Open the material fields in Parameter Sweep or Particle Explorer to apply these values."),
                            html.A("Back to documentation hub ->", href="/documentation", className="inline-action"),
                        ],
                    ),
                ],
            ),
        ],
    )
