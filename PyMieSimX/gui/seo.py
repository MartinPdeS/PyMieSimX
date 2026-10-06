"""Page metadata for direct requests and navigation within the Dash shell."""

from html import escape
import json

from dash import Dash, Input, Output
from flask import has_request_context, request


PAGE_METADATA = {
    "/examples": {
        "title": "Mie Scattering Examples — Nanoparticle Resonances & More | PyMieSimX",
        "description": "Explore six Mie scattering examples: gold and silver nanoparticle resonances, silica size sweeps, gold nanoshells, angular scattering, and suspension optics.",
    },
    "/": {
        "title": "Mie Scattering Calculator & Mie Theory Simulator | PyMieSimX",
        "description": "Calculate Mie scattering in your browser with PyMieSimX. Explore single particles, run parameter sweeps, and export results with the PyMieSim solver.",
    },
    "/single": {
        "title": "Mie Scattering Calculator — Single Scatterer | PyMieSimX",
        "description": "Explore nanoparticle scattering with the Single Scatterer calculator. Configure a source and particle to inspect angular scattering, polarization, and fields.",
    },
    "/experiment": {
        "title": "Mie Parameter Sweep — Parameter Scan | PyMieSimX",
        "description": "Run a Mie parameter sweep over source, particle, and detector settings. Plot scattering measures and export results as CSV with Parameter Scan.",
    },
    "/population": {
        "title": "Particle Population Scattering — Ensemble Optics | PyMieSimX",
        "description": "Explore optical scattering from particle size distributions with Ensemble Optics. Configure particle populations and compare their scattering response.",
    },
    "/documentation": {
        "title": "Mie Scattering Simulation Guide — Documentation | PyMieSimX",
        "description": "Learn to configure PyMieSimX scattering simulations, explore single particles, run parameter scans, and interpret optical inputs and results.",
    },
    "/documentation/install-local": {
        "title": "Local Installation — Documentation | PyMieSimX",
        "description": "Install PyMieSimX locally to run the Mie scattering GUI on your computer and use the Python API for optical simulations.",
    },
    "/documentation/sellmeier": {
        "title": "Sellmeier Refractive Index — Documentation | PyMieSimX",
        "description": "Learn how to specify wavelength-dependent refractive indices with Sellmeier coefficients for optical materials in PyMieSimX.",
    },
    "/documentation/field-syntax": {
        "title": "Input and Sweep Syntax — Documentation | PyMieSimX",
        "description": "Configure scientific inputs, physical units, and parameter ranges in PyMieSimX. Learn the field syntax for Mie scattering parameter sweeps.",
    },
    "/citation": {
        "title": "Citation | PyMieSimX",
        "description": "Find the publication and citation information for PyMieSim, the open-source solver used by PyMieSimX scattering simulations.",
    },
    "/settings": {
        "title": "Settings | PyMieSimX",
        "description": "Customize the appearance and plotting preferences of your PyMieSimX workspace.",
    },
    "/admin": {
        "title": "Administration | PyMieSimX",
        "description": "PyMieSimX administration dashboard.",
    },
}


class SearchDash(Dash):
    """Include route-specific metadata in the initial HTML response."""

    def interpolate_index(self, **kwargs):
        path = request.path if has_request_context() else "/"
        metadata = PAGE_METADATA.get(path, PAGE_METADATA["/"])
        kwargs["title"] = escape(metadata["title"])
        kwargs["metas"] += f'<meta name="description" content="{escape(metadata["description"], quote=True)}">'
        if has_request_context() and path in PAGE_METADATA:
            kwargs["metas"] += f'<link rel="canonical" href="{escape(request.base_url, quote=True)}">'
        return super().interpolate_index(**kwargs)


def register_page_metadata(application: Dash) -> None:
    """Keep head metadata current when Dash navigates without a full reload."""
    application.clientside_callback(
        """function(pathname) {
            const pages = """ + json.dumps(PAGE_METADATA) + """;
            const metadata = pages[pathname || '/'] || pages['/'];
            document.title = metadata.title;
            let description = document.head.querySelector('meta[name="description"]');
            if (!description) {
                description = document.createElement('meta');
                description.name = 'description';
                document.head.appendChild(description);
            }
            description.content = metadata.description;
            const canonical = document.head.querySelector('link[rel="canonical"]');
            if (canonical) canonical.href = window.location.origin + (pathname || '/');
            return pathname || '/';
        }""",
        Output("page-metadata", "data"),
        Input("url", "pathname"),
    )
