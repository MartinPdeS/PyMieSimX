"""Entry point for launching the PyMieSimX dashboard."""

import argparse
import logging
import sys


def _build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the dashboard launcher."""
    parser = argparse.ArgumentParser(description="Launch the PyMieSimX dashboard.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface for the Dash server.")
    parser.add_argument("--port", default="8050", help="Port for the Dash server.")
    parser.add_argument("--debug", action="store_true", help="Enable Dash debug mode and verbose debug logging.")
    parser.add_argument("--no-browser", action="store_true", help="Start the server without opening a browser window.")
    return parser


def configure_logging(*, debug: bool, log_level: str = "INFO") -> int:
    """Configure application logging using RosettaX's console format."""
    resolved_level = logging.DEBUG if debug else getattr(logging, str(log_level).upper(), logging.INFO)
    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("PyMieSimX").setLevel(resolved_level)
    return resolved_level


def main(argv: list[str] | None = None) -> None:
    """Launch the PyMieSimX dashboard from a console entry point."""
    args = _build_argument_parser().parse_args(argv)
    configure_logging(debug=args.debug)
    from PyMieSimX.gui.interface import OpticalSetupGUI

    OpticalSetupGUI().run(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
