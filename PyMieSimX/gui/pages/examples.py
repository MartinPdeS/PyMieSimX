"""Curated examples that open reproducible, automatically run simulations."""

from urllib.parse import urlencode

from dash import html

from PyMieSimX.gui.components import Card
from PyMieSimX.gui.defaults import DEFAULT_PLOT_SETTINGS
from PyMieSimX.gui.schemas import SECTION_FIELDS, SINGLE_SOURCE_FIELDS, SINGLE_SCATTERER_FIELDS
from PyMieSimX.gui.sharing import control_key, encode_simulation


GOLD = "main/Au/Olmon-ev"
SILVER = "main/Ag/Johnson"
SILICA = "main/SiO2/Malitson"


def _fields(section, specs, values):
    return {control_key({"kind": "field", "section": section, "name": spec.name}):
            values.get(spec.name, spec.default) for spec in specs}


def _sweep(wavelength, particles, *, model="SphereSet", axis="wavelength", measures=None):
    controls = {
        "source-type": "PlaneWaveSet", "scatterer-type": model, "detector-type": "None",
        "measure-select": measures or ["Qsca", "Qabs", "Qext"],
        "x-axis-select": axis, "plot-experiment-projection": "cartesian",
        **_fields("source", SECTION_FIELDS["source"]["PlaneWaveSet"], {"wavelength": wavelength}),
        **_fields("scatterer", SECTION_FIELDS["scatterer"][model], particles),
    }
    return {"v": 1, "page": "/experiment", "controls": controls, "plot_settings": dict(DEFAULT_PLOT_SETTINGS)}


def _angular():
    controls = {
        "single-source-type": "PlaneWave", "single-scatterer-type": "Sphere",
        "single-representation": "s1s2", "single-projection": "polar_1d", "single-sampling": "180",
        "single-nearfield-mode": ["absolute"], "single-include-incident-field": ["include"],
        **_fields("single-source", SINGLE_SOURCE_FIELDS["PlaneWave"], {"wavelength": "633"}),
        **_fields("single-scatterer", SINGLE_SCATTERER_FIELDS["Sphere"], {
            "diameter": "1000", "material": "organic/polystyrene/Sultanova", "medium": "1.33"}),
    }
    return {"v": 1, "page": "/single", "controls": controls, "plot_settings": dict(DEFAULT_PLOT_SETTINGS)}


def _suspension():
    controls = {f"population-{name}": value for name, value in {
        "wavelength": "633", "distribution": "lognormal", "diameter": "500", "width": "1.25",
        "minimum": "100", "maximum": "1500", "sampling": "96", "concentration-basis": "number",
        "concentration": "1e8",
    }.items()}
    controls.update({control_key({"kind": "field", "section": "population", "name": name}): value
                     for name, value in {"material": SILICA, "medium": "1.33"}.items()})
    return {"v": 1, "page": "/population", "controls": controls, "plot_settings": {}}


EXAMPLES = (
    {
        "id": "gold-resonance", "title": "Gold nanoparticle resonances", "topic": "Plasmonics", "color": "yellow",
        "description": "Compare the scattering, absorption, and extinction spectra of a gold nanosphere in water.",
        "observe": "Find the extinction peak and compare the contributions of scattering and absorption.",
        "parameters": [("Particle", "80 nm gold sphere"), ("Wavelength", "400–850 nm · 181 points"), ("Medium", "n = 1.33")],
        "setup": _sweep("400:850:181", {"diameter": "80", "material": GOLD, "medium": "1.33"}),
        "reference": ("Gold optical data · Olmon", "https://refractiveindex.info/?shelf=main&book=Au&page=Olmon-ev"),
    },
    {
        "id": "silver-resonance", "title": "Silver nanoparticle resonances", "topic": "Plasmonics", "color": "cyan",
        "description": "Explore the wavelength-dependent response of a silver nanosphere immersed in water.",
        "observe": "Locate the resonance and compare its spectral shape with the gold example.",
        "parameters": [("Particle", "60 nm silver sphere"), ("Wavelength", "300–650 nm · 141 points"), ("Medium", "n = 1.33")],
        "setup": _sweep("300:650:141", {"diameter": "60", "material": SILVER, "medium": "1.33"}),
        "reference": ("Silver optical data · Johnson & Christy", "https://refractiveindex.info/?shelf=main&book=Ag&page=Johnson"),
    },
    {
        "id": "silica-size", "title": "From Rayleigh to Mie scattering", "topic": "Particle size", "color": "blue",
        "description": "Sweep the diameter of a silica sphere at a fixed wavelength to explore how scattering changes with size.",
        "observe": "Follow the transition from weak small-particle scattering to the oscillations of larger spheres.",
        "parameters": [("Particle", "Silica · 30–1600 nm diameter"), ("Wavelength", "633 nm"), ("Medium", "n = 1.00")],
        "setup": _sweep("633", {"diameter": "30:1600:160", "material": SILICA, "medium": "1.0"},
                        axis="diameter", measures=["Qsca", "Qext"]),
        "reference": ("Silica optical data · Malitson", "https://refractiveindex.info/?shelf=main&book=SiO2&page=Malitson"),
    },
    {
        "id": "gold-nanoshell", "title": "Tune a gold nanoshell", "topic": "Core–shell particles", "color": "purple",
        "description": "Compare three gold shell thicknesses around the same silica core across a wavelength sweep.",
        "observe": "Compare the extinction peaks as the shell thickness changes while the core diameter stays fixed.",
        "parameters": [("Core", "80 nm silica diameter"), ("Gold shell", "5, 15, and 30 nm thick"), ("Wavelength", "450–1100 nm · n = 1.33")],
        "setup": _sweep("450:1100:161", {"core_diameter": "80", "shell_thickness": "5,15,30",
                         "core_material": SILICA, "shell_material": GOLD, "medium": "1.33"}, model="CoreShellSet"),
        "reference": ("Gold optical data · Olmon", "https://refractiveindex.info/?shelf=main&book=Au&page=Olmon-ev"),
    },
    {
        "id": "bead-angular", "title": "Where does a bead scatter light?", "topic": "Angular scattering", "color": "green",
        "description": "Inspect the two angular scattering amplitudes of a micrometre-sized polystyrene bead in water.",
        "observe": "Compare |S1| and |S2| in the polar plot to explore angular lobes and polarization dependence.",
        "parameters": [("Particle", "1 µm polystyrene bead"), ("Wavelength", "633 nm · linear polarization"), ("View", "Polar S1 / S2 amplitudes · n = 1.33")],
        "setup": _angular(),
        "reference": ("Polystyrene optical data · Sultanova", "https://refractiveindex.info/?shelf=organic&book=polystyrene&page=Sultanova"),
    },
    {
        "id": "silica-suspension", "title": "Optics of a silica suspension", "topic": "Ensemble optics", "color": "blue",
        "description": "Combine a lognormal size distribution and concentration to calculate the optical properties of a dilute suspension.",
        "observe": "Inspect scattering and absorption coefficients, albedo, and the scattering-weighted anisotropy.",
        "parameters": [("Distribution", "500 nm median · GSD 1.25"), ("Concentration", "10⁸ particles/mL"), ("Illumination", "633 nm · n = 1.33")],
        "setup": _suspension(),
        "reference": ("Silica optical data · Malitson", "https://refractiveindex.info/?shelf=main&book=SiO2&page=Malitson"),
    },
)


def example_link(example):
    """Build a portable link using the same format as user-shared simulations."""
    setup = example["setup"]
    return setup["page"] + "?" + urlencode({"simulation": encode_simulation(setup)})


def build_examples_page():
    """Show six independent starting points without computing on page load."""
    return html.Div(className="page-content-stack examples-page", children=[
        html.Section(className="page-hero", children=[
            html.P("Start with a physical question", className="eyebrow"),
            html.H1("Examples"),
            html.P("Six ready-to-run simulations. Open an example to restore its setup, run it automatically, and explore the results.", className="hero-text"),
        ]),
        html.Div(className="examples-grid", children=[_example_card(example, index) for index, example in enumerate(EXAMPLES, 1)]),
    ])


def _example_card(example, index):
    workspace = {"/experiment": "Parameter Scan", "/single": "Single Scatterer", "/population": "Ensemble Optics"}[example["setup"]["page"]]
    reference_label, reference_url = example["reference"]
    return html.Article(id=f"example-{example['id']}", className=Card.classes(color=example["color"], extra="example-card"), children=[
        html.Div(className="example-card-heading", children=[html.Span(f"{index:02d}", className="example-number"), html.Span(example["topic"], className="example-topic")]),
        html.H2(example["title"]),
        html.P(example["description"], className="example-description"),
        html.Dl(className="example-parameters", children=[html.Div([html.Dt(label), html.Dd(value)]) for label, value in example["parameters"]]),
        html.Div(className="example-observe", children=[html.Strong("What to look for"), html.P(example["observe"])]),
        html.A(reference_label, href=reference_url, target="_blank", rel="noopener noreferrer", className="example-reference"),
        html.Div(className="example-card-actions", children=[html.Span(workspace), html.A("Open simulation & results →", href=example_link(example), className="example-open toolbar-button toolbar-button-primary")]),
    ])
