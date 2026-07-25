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

    standard_rows = [
        html.Tr(
            [
                html.Td(str(row.get("material", ""))),
                html.Td(str(row.get("formula", "—"))),
                html.Td(str(row.get("B1", "—"))),
                html.Td(str(row.get("B2", "—"))),
                html.Td(str(row.get("B3", "—"))),
                html.Td(str(row.get("C1_um2", "—"))),
                html.Td(str(row.get("C2_um2", "—"))),
                html.Td(str(row.get("C3_um2", "—"))),
            ]
        )
        for row in sellmeier
        if isinstance(row, dict) and row.get("formula") in {"Formula 1", "Formula 2"}
    ]
    alternative_rows = [
        html.Tr([html.Td(str(row.get("material", ""))), html.Td(str(row.get("formula", "—"))), html.Td(str(row.get("parameters", "—")))])
        for row in sellmeier
        if isinstance(row, dict) and row.get("formula") not in {"Formula 1", "Formula 2", "Tabulated"}
    ]
    tabulated_rows = [
        html.Tr([html.Td(str(row.get("material", ""))), html.Td(str(row.get("parameters", "Tabulated n(lambda) and k(lambda) data")))])
        for row in sellmeier
        if isinstance(row, dict) and row.get("formula") == "Tabulated"
    ]

    return html.Div(
        className="page-content-stack documentation-page",
        children=[
            html.Section(
                className="page-hero documentation-page-hero",
                children=[
                    html.P("PyMieSim material model", className="eyebrow"),
                    html.H1("Material Models"),
                    html.P(
                        "Use this page as a quick reference when selecting or validating dispersive and tabulated materials.",
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
            _standard_sellmeier_section(standard_rows),
            _alternative_formula_section(alternative_rows),
            _tabulated_materials_section(tabulated_rows),
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


def _standard_sellmeier_section(rows):
    return html.Section(
        className=Card.classes(color="green", extra="panel documentation-detail-card"),
        children=[
            html.Div(className="card-header panel-header", children=[html.H2("Standard Sellmeier coefficients")]),
            html.Div(
                className="card-body",
                children=[
                    html.P("Formula 1 and Formula 2 materials use the B/C coefficient layout below. C values are shown in um^2."),
                    html.Table(
                        className="documentation-table",
                        children=[
                            html.Thead(html.Tr([html.Th("Material"), html.Th("Formula"), html.Th("B1"), html.Th("B2"), html.Th("B3"), html.Th("C1 (um^2)"), html.Th("C2 (um^2)"), html.Th("C3 (um^2)")])),
                            html.Tbody(rows),
                        ],
                    ),
                    html.P("Used formulas (lambda in micrometers):", className="documentation-callout"),
                    html.Div(className="documentation-formula-list", children=[
                        html.Div([html.Strong("Formula 1"), html.Code("n(lambda)^2 = 1 + sum(Bi*lambda^2 / (lambda^2 - Ci^2))")]),
                        html.Div([html.Strong("Formula 2"), html.Code("n(lambda)^2 = 1 + A + sum(Bi*lambda^2 / (lambda^2 - Ci))")]),
                    ]),
                ],
            ),
        ],
    )


def _alternative_formula_section(rows):
    return html.Section(
        className=Card.classes(color="orange", extra="panel documentation-detail-card"),
        children=[
            html.Div(className="card-header panel-header", children=[html.H2("Alternative formula parameters")]),
            html.Div(
                className="card-body",
                children=[
                    html.P("These materials are valid catalog entries, but their native coefficients do not fit the standard B/C table."),
                    html.Table(
                        className="documentation-table",
                        children=[
                            html.Thead(html.Tr([html.Th("Material"), html.Th("Formula"), html.Th("Native parameters")])),
                            html.Tbody(rows),
                        ],
                    ),
                    html.P("Used formulas (lambda in micrometers):", className="documentation-callout"),
                    html.Div(className="documentation-formula-list", children=[
                        html.Div([html.Strong("Formula 5"), html.Code("n(lambda) = 1 + A + sum(Bi*lambda^Ci)")]),
                        html.Div([html.Strong("Formula 6"), html.Code("n(lambda) = Bi / (Ci - lambda^-2)")]),
                    ]),
                ],
            ),
        ],
    )


def _tabulated_materials_section(rows):
    return html.Section(
        className=Card.classes(color="purple", extra="panel documentation-detail-card"),
        children=[
            html.Div(className="card-header panel-header", children=[html.H2("Tabulated material data")]),
            html.Div(
                className="card-body",
                children=[
                    html.P("These materials use wavelength-dependent n(lambda) and k(lambda) data rather than Sellmeier coefficients."),
                    html.Table(
                        className="documentation-table",
                        children=[
                            html.Thead(html.Tr([html.Th("Material"), html.Th("Available data")])),
                            html.Tbody(rows),
                        ],
                    ),
                    html.P("These materials are evaluated from tabulated wavelength-dependent data; no closed-form Sellmeier formula is used.", className="documentation-callout"),
                    html.P("You can still use the RI toggle for direct n or n+ik entry when dispersion is not required.", className="documentation-callout"),
                ],
            ),
        ],
    )
