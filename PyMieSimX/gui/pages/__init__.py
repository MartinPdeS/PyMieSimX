"""Page modules for the PyMieSim Dash application."""

from .documentation import build_documentation_page
from .field_syntax import build_field_syntax_page
from .citation import build_citation_page
from .home import build_home_page
from .install_local import build_install_local_page
from .sellmeier import build_sellmeier_page
from .settings import build_settings_page

__all__ = ["build_citation_page", "build_documentation_page", "build_field_syntax_page", "build_home_page", "build_install_local_page", "build_sellmeier_page", "build_settings_page"]
