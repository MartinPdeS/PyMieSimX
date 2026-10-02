"""Small browser-level smoke suite for the critical dashboard workflow."""

import pytest
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


def _wait_for_sidebar_transition(dash_duo):
    """Wait for the panel to settle before clicking its controls or the page."""
    WebDriverWait(dash_duo.driver, 10).until(
        lambda driver: driver.execute_script(
            "return document.querySelector('#experiment-right-sidebar').getAnimations()"
            ".every(animation => animation.playState !== 'running')"
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
