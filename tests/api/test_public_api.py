"""Public package entry points and version contract."""

import PyMieSimX
from PyMieSimX._version import __version__ as documented_version


def test_public_api_exposes_computational_entry_points_without_gui_symbols():
    assert callable(PyMieSimX.run_experiment)
    assert callable(PyMieSimX.build_figure)
    assert PyMieSimX.MAX_SWEEP_COMBINATIONS == 50_000
    assert PyMieSimX.MAX_RESULT_PAYLOAD_BYTES > 0
    assert isinstance(PyMieSimX.__version__, str)
    assert PyMieSimX.__version__ == documented_version
