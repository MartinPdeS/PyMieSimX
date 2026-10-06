#!/usr/bin/env python3
"""Verify the installed Conda package from outside the source checkout."""

import importlib
import json
from pathlib import Path
import subprocess
import sys


def main() -> None:
    prefix = Path(sys.prefix).resolve()
    print(f"Verification Python: {sys.executable}", flush=True)
    print(f"Import paths: {sys.path}", flush=True)
    for manifest in (prefix / "conda-meta").glob("pymiesimx-*.json"):
        record = json.loads(manifest.read_text())
        print(f"Installed package: {record['name']} {record['version']}", flush=True)
        print(f"Installed files: {record['files']}", flush=True)
    module = importlib.import_module("PyMieSimX")
    location = Path(module.__file__).resolve()
    if not location.is_relative_to(prefix):
        raise RuntimeError(f"Imported {location} outside the Conda test environment {prefix}")
    launcher = prefix / ("Scripts/pymiesimx.exe" if sys.platform == "win32" else "bin/pymiesimx")
    subprocess.run([str(launcher), "--help"], check=True)


if __name__ == "__main__":
    main()
