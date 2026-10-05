"""Small browser-level smoke suite for the critical dashboard workflow."""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from io import StringIO
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from PyMieSimX.gui.interface import create_dash_app
from PyMieSimX.gui.jobs import ExperimentJobManager
from PyMieSimX.gui.seo import PAGE_METADATA


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


def test_page_metadata_tracks_navigation_and_direct_visits(dash_duo):
    dash_duo.driver.set_window_size(1440, 1000)
    dash_duo.start_server(create_dash_app())

    def wait_for_metadata(path):
        metadata = PAGE_METADATA[path]
        WebDriverWait(dash_duo.driver, 10).until(
            lambda driver: driver.title == metadata["title"]
            and driver.execute_script(
                'return Array.from(document.head.querySelectorAll(\'meta[name="description"]\'))'
                '.map(element => element.content);'
            ) == [metadata["description"]]
        )

    wait_for_metadata("/")
    for route, label in (("single", "Single Scatterer"), ("experiment", "Parameter Scan")):
        dash_duo.wait_for_text_to_equal(f"#sidebar-link-{route}", label)
        dash_duo.find_element(f"#sidebar-link-{route}").click()
        dash_duo.wait_for_element(".workspace-intro")
        wait_for_metadata(f"/{route}")
        dash_duo.driver.refresh()
        dash_duo.wait_for_element(".workspace-intro")
        wait_for_metadata(f"/{route}")

    dash_duo.find_element("#sidebar-link-home").click()
    dash_duo.wait_for_text_to_equal("h1", "PyMieSim")
    wait_for_metadata("/")


@pytest.mark.parametrize("viewport", [(1440, 1000), (390, 844)], ids=["desktop", "mobile"])
def test_home_star_button_below_support_developer(dash_duo, viewport):
    dash_duo.driver.set_window_size(*viewport)
    dash_duo.start_server(create_dash_app())
    support = dash_duo.wait_for_element("#home-support-developer")
    star = dash_duo.wait_for_element("#home-star-repository")
    assert star.is_displayed()
    assert star.find_element("css selector", ".home-support-label").text == "Star PyMieSim on GitHub"
    assert star.get_attribute("href") == "https://github.com/MartinPdeS/PyMieSim"
    assert star.get_attribute("target") == "_blank"
    assert set(star.get_attribute("rel").split()) == {"noopener", "noreferrer"}
    # Read both boxes in one frame after fonts load; separate WebDriver reads
    # can straddle a font-induced layout change on the mobile page.
    geometry = WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.execute_script(
        "if (document.fonts.status !== 'loaded') return null;"
        "const support = arguments[0].getBoundingClientRect(), star = arguments[1].getBoundingClientRect();"
        "if (star.top < support.bottom || Math.abs(star.left-support.left) > .01 || star.right > innerWidth) return null;"
        "return {supportBottom: support.bottom, supportLeft: support.left, starTop: star.top,"
        "starLeft: star.left, starRight: star.right, viewportWidth: innerWidth};", support, star,
    ))
    assert geometry["starTop"] >= geometry["supportBottom"]
    assert geometry["starLeft"] == pytest.approx(geometry["supportLeft"])
    assert geometry["starRight"] <= geometry["viewportWidth"]


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


def _population_control(dash_duo, selector):
    """Open the correct side panel and wait for real hit testing before interaction."""
    if selector in {"#population-compute", "#population-export"}:
        active_tabs = dash_duo.find_elements(".population-page .sidebar-tab.active")
        if active_tabs:
            active_tabs[0].click()
            dash_duo.wait_for_class_to_equal("#population-right-sidebar", "right-sidebar-panel")
            _wait_for_sidebar_transition(dash_duo, "population-right-sidebar")
    else:
        if selector == "#population-wavelength" or selector.startswith(("#population-material-field", "#population-medium-field")):
            panel = "particle"
        elif selector.startswith("#population-concentration"):
            panel = "concentration"
        else:
            panel = "distribution"
        tab = dash_duo.find_element(f"#population-tab-{panel}")
        if "active" not in tab.get_attribute("class").split():
            tab.click()
            dash_duo.wait_for_contains_class("#population-right-sidebar", "open")
            _wait_for_sidebar_transition(dash_duo, "population-right-sidebar")
    element = dash_duo.find_element(selector)
    dash_duo.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'})", element)
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.execute_script(
        "const e = arguments[0], r = e.getBoundingClientRect();"
        "const hit = document.elementFromPoint(r.x + r.width/2, r.y + r.height/2);"
        "return r.y >= 0 && r.bottom <= innerHeight && (hit === e || e.contains(hit));", element,
    ))
    return element


@pytest.mark.parametrize("viewport", [(1440, 1000), (390, 844)], ids=["desktop", "mobile"])
def test_population_optics_preview_validation_compute_and_export(dash_duo, viewport):
    dash_duo.driver.set_window_size(*viewport)
    if viewport[0] < 500:
        dash_duo.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": viewport[0], "height": viewport[1], "deviceScaleFactor": 1, "mobile": False,
        })
    assert dash_duo.driver.execute_script("return window.innerWidth") == viewport[0]
    dash_duo.start_server(create_dash_app())
    dash_duo.find_element("#sidebar-link-population").click()
    header = dash_duo.wait_for_element(".population-page .page-hero")
    assert "Ensemble Optics" not in header.text
    dash_duo.wait_for_element("#population-preview .barlayer .trace")
    assert dash_duo.find_element("#population-export").get_attribute("disabled")
    assert dash_duo.find_elements("#measure-select") == []
    dash_duo.wait_for_class_to_equal("#population-right-sidebar", "right-sidebar-panel")
    assert not dash_duo.find_element("#population-wavelength").is_displayed()
    assert not dash_duo.find_element("#population-width").is_displayed()
    width = _population_control(dash_duo, "#population-width")
    assert dash_duo.find_element("#population-panel-distribution").is_displayed()
    assert not dash_duo.find_element("#population-panel-particle").is_displayed()
    # The active tab collapses the panel, and reopening preserves the inputs.
    dash_duo.find_element("#population-tab-distribution").click()
    dash_duo.wait_for_class_to_equal("#population-right-sidebar", "right-sidebar-panel")
    _wait_for_sidebar_transition(dash_duo, "population-right-sidebar")
    assert not width.is_displayed()
    _population_control(dash_duo, "#population-width")
    assert width.get_attribute("value") == "1.2"
    assert dash_duo.find_element("#population-width-label").text == "Geometric standard deviation"
    wavelength = dash_duo.find_element("#population-wavelength")
    _population_control(dash_duo, "#population-wavelength").clear()
    wavelength.send_keys("-1", Keys.TAB)
    _population_control(dash_duo, "#population-compute").click()
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: "Unable to compute" in dash_duo.find_element("#population-status").text)
    assert dash_duo.find_element("#population-compute").is_enabled()
    _population_control(dash_duo, "#population-wavelength").clear()
    wavelength.send_keys("650", Keys.TAB)
    _population_control(dash_duo, "#population-compute").click()
    WebDriverWait(dash_duo.driver, 20).until(lambda driver: "Completed" in dash_duo.find_element("#population-status").text)
    rows = dash_duo.find_elements("#population-results tbody tr")
    assert len(rows) == 18
    table = dash_duo.find_element("#population-results").text
    for property_name in ("mu_s", "mu_a", "mu_ext", "mu_s_prime", "albedo", "g", "mean_Qsca_number", "mean_Qsca_area"):
        assert property_name in table
    assert "mm^-1" in table
    assert dash_duo.find_element("#population-export").is_enabled()
    _population_control(dash_duo, "#population-export").click()
    download = Path(dash_duo.download_path) / "ensemble-optics.csv"
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: download.exists())
    csv_text = download.read_text()
    exported = pd.read_csv(StringIO(csv_text.split("\n\n")[0]))
    assert len(exported) == 18
    assert exported.loc[0, "parameter"] == "mu_s"
    assert exported.loc[0, "unit"] == "mm^-1"
    assert "diameter_nm,number_fraction" in csv_text
    assert dash_duo.find_element("#population-compute").is_enabled()
    _population_control(dash_duo, "#population-distribution")
    dash_duo.select_dcc_dropdown("#population-distribution", "Gaussian (truncated)")
    dash_duo.wait_for_text_to_equal("#population-width-label", "Standard deviation [nm]")
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: dash_duo.find_element("#population-width").get_attribute("value") == "50")
    dash_duo.wait_for_no_elements("#population-results tbody tr")
    assert dash_duo.find_element("#population-export").get_attribute("disabled")
    _population_control(dash_duo, "#population-width").clear()
    width.send_keys("0", Keys.TAB)
    dash_duo.wait_for_text_to_equal("#population-preview-error", "Gaussian standard deviation must be finite and positive.")
    _population_control(dash_duo, "#population-width").clear()
    width.send_keys("50", Keys.TAB)
    dash_duo.wait_for_text_to_equal("#population-preview-error", "")
    _population_control(dash_duo, "#population-concentration-basis")
    dash_duo.select_dcc_dropdown("#population-concentration-basis", "Particle volume fraction")
    dash_duo.wait_for_text_to_equal("#population-concentration-label", "Particle volume fraction [0–1]")
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: dash_duo.find_element("#population-concentration").get_attribute("value") == "0.001")
    _population_control(dash_duo, "#population-compute").click()
    WebDriverWait(dash_duo.driver, 20).until(lambda driver: "Completed" in dash_duo.find_element("#population-status").text)
    assert "volume_fraction" in dash_duo.find_element("#population-results").text
    dash_duo.find_element("#population-tab-model").click()
    dash_duo.wait_for_contains_class("#population-right-sidebar", "open")
    _wait_for_sidebar_transition(dash_duo, "population-right-sidebar")
    assert "independent scattering" in dash_duo.find_element("#population-panel-model").text
    assert not dash_duo.find_element("#population-panel-concentration").is_displayed()
    dash_duo.find_element("#population-tab-model").click()
    dash_duo.wait_for_class_to_equal("#population-right-sidebar", "right-sidebar-panel")
    _wait_for_sidebar_transition(dash_duo, "population-right-sidebar")
    assert dash_duo.driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth")
    assert dash_duo.get_logs() == []


@pytest.mark.parametrize("viewport", [(1440, 1000), (390, 844)], ids=["desktop", "mobile"])
def test_home_ensemble_card_and_scientific_workspace_names(dash_duo, viewport):
    dash_duo.driver.set_window_size(*viewport)
    if viewport[0] < 500:
        dash_duo.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": viewport[0], "height": viewport[1], "deviceScaleFactor": 1, "mobile": False,
        })
    dash_duo.start_server(create_dash_app())
    dash_duo.wait_for_text_to_equal("h1", "PyMieSim")
    for route, title in (("single", "Single Scatterer"), ("experiment", "Parameter Scan"), ("population", "Ensemble Optics")):
        dash_duo.wait_for_text_to_equal(f"#sidebar-link-{route}", title)
        dash_duo.wait_for_text_to_equal(f"#home-workflow-{route} .home-section-header", title)
    card = dash_duo.find_element("#home-workflow-population")
    assert "albedo" in card.text
    assert "concentration" in card.text
    dash_duo.wait_for_element("#home-workflow-population .scatterlayer .trace")
    assert len(dash_duo.find_elements("#home-workflow-population .scatterlayer .trace")) == 2
    assert card.rect["x"] + card.rect["width"] <= viewport[0]
    assert dash_duo.driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth")
    link = dash_duo.find_element("#home-workflow-population .home-workflow-button")
    assert link.text == "Open Ensemble Optics"
    assert link.get_attribute("href").endswith("/population")
    dash_duo.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'})", link)
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.execute_script(
        "const e = arguments[0], r = e.getBoundingClientRect();"
        "return document.elementFromPoint(r.x+r.width/2, r.y+r.height/2) === e;", link,
    ))
    link.click()
    dash_duo.wait_for_element("#population-preview .barlayer .trace")
    dash_duo.wait_for_contains_class("#sidebar-link-population", "active")
    assert "Ensemble Optics" not in dash_duo.find_element(".population-page .page-hero").text
    assert dash_duo.get_logs() == []



@pytest.mark.parametrize("viewport", [(1440, 1000), (390, 844)], ids=["desktop", "mobile"])
def test_ensemble_optical_material_toggles_preserve_ri_and_compute_named_materials(dash_duo, viewport):
    from PyMieSimX.gui.material_catalog import material_dropdown_options

    dash_duo.driver.set_window_size(*viewport)
    if viewport[0] < 500:
        dash_duo.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": viewport[0], "height": viewport[1], "deviceScaleFactor": 1, "mobile": False,
        })
    dash_duo.start_server(create_dash_app())
    dash_duo.find_element("#sidebar-link-population").click()
    dash_duo.wait_for_element("#population-preview .barlayer .trace")
    for name, ri, replacement in (("material", "1.5+0.01j", "1.6+0.02j"), ("medium", "1.33", "1.34")):
        wrapper = f"#population-{name}-field"
        input_selector = f"{wrapper} input"
        toggle_selector = f"{wrapper} .material-mode-toggle"
        dropdown_selector = f"{wrapper} .material-name-select"
        ri_input = _population_control(dash_duo, input_selector)
        assert ri_input.get_attribute("value") == ri
        assert not dash_duo.find_element(dropdown_selector).is_displayed()
        ri_input.clear()
        ri_input.send_keys(replacement, Keys.TAB)
        _population_control(dash_duo, toggle_selector).click()
        dash_duo.wait_for_contains_class(toggle_selector, "is-material")
        WebDriverWait(dash_duo.driver, 10).until(lambda driver: dash_duo.find_element(dropdown_selector).is_displayed())
        assert not ri_input.is_displayed()
        options = material_dropdown_options(medium=name == "medium")
        option = next(option for option in options if option["label"].startswith("Water")) if name == "medium" else options[0]
        _population_control(dash_duo, dropdown_selector)
        dash_duo.select_dcc_dropdown(dropdown_selector, option["label"])
        WebDriverWait(dash_duo.driver, 10).until(lambda driver: ri_input.get_attribute("value") == option["value"])
        assert not dash_duo.find_elements(f"{wrapper} .field-input-invalid")
        _population_control(dash_duo, toggle_selector).click()
        dash_duo.wait_for_contains_class(toggle_selector, "is-index")
        WebDriverWait(dash_duo.driver, 10).until(lambda driver: ri_input.get_attribute("value") == replacement)
        assert ri_input.is_displayed()
        assert not dash_duo.find_element(dropdown_selector).is_displayed()
        _population_control(dash_duo, toggle_selector).click()
        dash_duo.wait_for_contains_class(toggle_selector, "is-material")
        WebDriverWait(dash_duo.driver, 10).until(lambda driver: ri_input.get_attribute("value") == option["value"])
    _population_control(dash_duo, "#population-compute").click()
    WebDriverWait(dash_duo.driver, 20).until(lambda driver: "Completed" in dash_duo.find_element("#population-status").text)
    rows = dash_duo.find_elements("#population-results tbody tr")
    assert len(rows) == 18
    assert float(rows[0].find_elements("css selector", "td")[1].text) > 0
    assert dash_duo.find_element("#population-export").is_enabled()
    # Returning to RI after a named-material run invalidates results and restores the typed index.
    _population_control(dash_duo, "#population-material-field .material-mode-toggle").click()
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: dash_duo.find_element("#population-material-field input").get_attribute("value") == "1.6+0.02j")
    dash_duo.wait_for_no_elements("#population-results tbody tr")
    assert dash_duo.find_element("#population-export").get_attribute("disabled")
    assert dash_duo.get_logs() == []
