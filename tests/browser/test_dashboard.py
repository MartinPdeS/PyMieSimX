"""Small browser-level smoke suite for the critical dashboard workflow."""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from PyMieSimX.gui.interface import create_dash_app
from PyMieSimX.gui.jobs import ExperimentJobManager


@pytest.fixture(autouse=True)
def isolated_experiment_jobs(dash_duo, monkeypatch):
    """Finish each worker before Dash's runner tears down its server threads."""
    manager = ExperimentJobManager()
    monkeypatch.setattr("PyMieSimX.gui.callbacks.experiment_jobs", manager)
    yield manager
    manager._executor.shutdown(wait=True)


def _wait_for_sidebar_transition(dash_duo, sidebar_id="experiment-right-sidebar"):
    """Wait for the panel to settle before clicking its controls or the page."""
    WebDriverWait(dash_duo.driver, 10).until(
        lambda driver: driver.execute_script(
            "return document.getElementById(arguments[0]).getAnimations()"
            ".every(animation => animation.playState !== 'running')", sidebar_id,
        )
    )


@pytest.mark.parametrize("viewport", [(1440, 1000), (960, 1000)], ids=["desktop", "compact"])
def test_navigation_validation_execution_plot_and_export_controls(dash_duo, viewport):
    # Chrome's default headless window puts Run below the visible compact header.
    dash_duo.driver.set_window_size(*viewport)
    dash_duo.start_server(create_dash_app())
    dash_duo.wait_for_text_to_equal("h1", "PyMieSim")
    assert dash_duo.find_elements(".home-metric-value") == []

    dash_duo.find_element("#sidebar-link-experiment").click()
    dash_duo.wait_for_element("#result-graph")
    dash_duo.wait_for_element("#export-csv")
    dash_duo.wait_for_text_to_equal("#experiment-run-status .status-banner span:last-child", "Ready. Click Run to start a sweep.")
    dash_duo.wait_for_element("#experiment-tab-source").click()
    dash_duo.wait_for_contains_class("#experiment-right-sidebar", "open")
    _wait_for_sidebar_transition(dash_duo)
    field = dash_duo.wait_for_element("#source-fields .field-input")

    input_element = field if field.tag_name == "input" else field.find_element("css selector", "input")
    input_element.click()
    input_element.clear()
    input_element.send_keys("-1", Keys.ENTER)
    dash_duo.wait_for_element("#source-fields .field-input-invalid")
    dash_duo.find_element("#experiment-tab-source").click()
    dash_duo.wait_for_class_to_equal("#experiment-right-sidebar", "right-sidebar-panel")
    _wait_for_sidebar_transition(dash_duo)
    dash_duo.find_element("#run-experiment-button").click()
    dash_duo.wait_for_element("#experiment-run-status .status-banner.error")
    assert "wavelength" in dash_duo.find_element("#experiment-run-status").text

    dash_duo.wait_for_class_to_equal("#experiment-right-sidebar", "right-sidebar-panel")
    dash_duo.find_element("#experiment-tab-source").click()
    dash_duo.wait_for_contains_class("#experiment-right-sidebar", "open")
    _wait_for_sidebar_transition(dash_duo)
    input_element.click()
    input_element.clear()
    input_element.send_keys("600:700:3", Keys.ENTER)
    dash_duo.wait_for_no_elements("#source-fields .field-input-invalid")
    dash_duo.find_element("#experiment-tab-source").click()
    dash_duo.wait_for_class_to_equal("#experiment-right-sidebar", "right-sidebar-panel")
    _wait_for_sidebar_transition(dash_duo)
    for measure in ("Qabs", "Qext"):
        dash_duo.select_dcc_dropdown("#measure-select", measure)
        dash_duo.find_element(".graph-axis-title").click()
    dash_duo.find_element("#run-experiment-button").click()
    dash_duo.wait_for_element("#experiment-run-status .status-banner.success", timeout=30)
    assert "6 result rows" in dash_duo.find_element("#experiment-run-status").text
    assert dash_duo.find_element("#run-experiment-button").is_enabled()
    assert dash_duo.find_element("#export-csv").is_enabled()
    dash_duo.wait_for_element("#result-graph .scatterlayer .trace")
    groups = dash_duo.driver.execute_script("return document.querySelector('#result-graph .js-plotly-plot').data.map(trace => trace.legendgroup)")
    assert set(groups) == {"Qsca", "Qabs", "Qext"}

    dash_duo.find_element("#sidebar-link-single").click()
    dash_duo.wait_for_element("#single-graph .plotly")
    dash_duo.wait_for_element("#export-single-csv")


@pytest.mark.parametrize("representation, projection, columns, row_count", [
    ("S1 / S2 amplitudes", None, ["series", "x", "value"], 48),
    ("Stokes I intensity", "2D heatmap", ["series", "x", "y", "value"], 576),
    ("Stokes I intensity", "3D radial surface", ["series", "x", "y", "z", "value"], 576),
])
def test_particle_explorer_downloads_csv(dash_duo, representation, projection, columns, row_count):
    dash_duo.driver.set_window_size(1440, 1000)
    dash_duo.start_server(create_dash_app())
    dash_duo.find_element("#sidebar-link-single").click()
    dash_duo.wait_for_element("#export-single-csv")
    assert not dash_duo.find_element("#export-single-csv").is_enabled()
    dash_duo.select_dcc_dropdown("#single-representation", representation)
    if projection:
        dash_duo.find_element("#single-tab-plot-options").click()
        dash_duo.wait_for_contains_class("#single-right-sidebar", "open")
        _wait_for_sidebar_transition(dash_duo, "single-right-sidebar")
        dash_duo.select_dcc_dropdown("#single-projection", projection)
        dash_duo.find_element("#single-tab-plot-options").click()
        dash_duo.wait_for_class_to_equal("#single-right-sidebar", "right-sidebar-panel")
        _wait_for_sidebar_transition(dash_duo, "single-right-sidebar")
    sampling = dash_duo.find_element("#single-sampling")
    sampling.clear()
    sampling.send_keys("24", Keys.ENTER)
    dash_duo.find_element("#run-single-button").click()
    WebDriverWait(dash_duo.driver, 30).until(lambda _: dash_duo.find_element("#export-single-csv").is_enabled())
    dash_duo.find_element("#export-single-csv").click()
    downloaded = Path(dash_duo.download_path) / "pymiesim_particle_explorer.csv"
    WebDriverWait(dash_duo.driver, 10).until(lambda _: downloaded.exists() and downloaded.stat().st_size > 0)
    frame = pd.read_csv(downloaded)
    assert list(frame.columns) == columns
    assert len(frame) == row_count
    assert np.isfinite(frame[columns[1:]].to_numpy()).all()
    if representation == "S1 / S2 amplitudes":
        assert set(frame.series) == {"|S1|", "|S2|"}
        assert frame.x.min() == pytest.approx(-180)
        assert frame.x.max() == pytest.approx(180)
    elif projection == "2D heatmap":
        assert frame.x.nunique() == 24
        assert frame.y.nunique() == 24
    else:
        assert (frame.value >= 0).all()
        assert frame.value.nunique() > 1
    assert dash_duo.get_logs() == []
