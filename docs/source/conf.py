"""Sphinx configuration for PyMieSimX."""

import subprocess
import sys
from pathlib import Path

from martinpdes_docs import configure


# API autodoc imports the calculation services, which resolve named PyOptik
# materials. Populate the catalogue on a fresh documentation runner.
try:
    from PyOptik.directories import user_data_path
except ImportError:
    user_data_path = None
else:
    catalog_path = Path(user_data_path) / "rii" / "catalog-nk.yml"
    if not catalog_path.is_file():
        subprocess.run(
            [sys.executable, "-m", "PyOptik", "setup", "--no-progress"],
            check=True,
        )


project = "PyMieSimX"
package = "PyMieSimX"
repository = "MartinPdeS/PyMieSimX"
author = "Martin Poinsinet de Sivry-Houle"

# PyMieSimX documents a stable Python API and its Dash application; it does
# not currently have executable gallery examples.
globals().update(
    configure(
        project=project,
        package=package,
        author=author,
        repository=repository,
        logo="_static/logo.svg",
        favicon="_static/favicon.svg",
        extensions=[
            "sphinx.ext.autodoc",
            "sphinx.ext.autosummary",
            "sphinx.ext.intersphinx",
            "sphinx.ext.napoleon",
            "sphinx.ext.viewcode",
            "sphinx.ext.todo",
            "sphinx_design",
        ],
    )
)

autodoc_default_options.update({"members": True})
html_context.update({"doc_path": "docs/source", "default_mode": "dark"})

intersphinx_mapping = {
    "numpy": ("https://numpy.org/devdocs", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "plotly": ("https://plotly.com/python-api-reference", None),
}
