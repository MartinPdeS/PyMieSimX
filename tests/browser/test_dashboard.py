"""Small browser-level smoke suite for the critical dashboard workflow."""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from io import StringIO
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException
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


@pytest.mark.parametrize("viewport", [(1440, 1000), (1280, 900), (390, 844), (320, 740)],
                         ids=["desktop", "compact-desktop", "mobile", "small-mobile"])
def test_workspace_cards_and_action_buttons_align_across_pages(dash_duo, viewport):
    dash_duo.driver.set_window_size(*viewport)
    dash_duo.start_server(create_dash_app())
    geometries = []
    for route in ("single", "experiment", "population"):
        dash_duo.driver.get(dash_duo.server_url + "/" + route)
        dash_duo.wait_for_element(".workspace-header")
        dash_duo.wait_for_element("#simulation-clipboard")
        geometry = WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.execute_script(
            "if (document.fonts.status !== 'loaded') return null;"
            "const card = document.querySelector('.workspace-header').getBoundingClientRect();"
            "const buttons = Array.from(document.querySelectorAll('.graph-toolbar .toolbar-button'))"
            ".filter(button => getComputedStyle(button).display !== 'none');"
            "return {top: card.top, height: card.height, bottom: card.bottom,"
            "buttons: buttons.map(button => button.getBoundingClientRect().top)};"
        ))
        assert len(geometry["buttons"]) == 3
        assert min(geometry["buttons"]) >= geometry["bottom"]
        geometries.append(geometry)
    for geometry in geometries[1:]:
        assert geometry["top"] == pytest.approx(geometries[0]["top"], abs=1)
        assert geometry["height"] == pytest.approx(geometries[0]["height"], abs=1)
        assert geometry["buttons"] == pytest.approx(geometries[0]["buttons"], abs=1)
    assert dash_duo.get_logs() == []


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
def test_examples_cards_open_all_six_simulations_and_run_automatically(dash_duo, viewport):
    from PyMieSimX.gui.pages.examples import EXAMPLES
    dash_duo.driver.set_window_size(*viewport)
    dash_duo.start_server(create_dash_app())
    dash_duo.find_element("#sidebar-link-examples").click()
    dash_duo.wait_for_text_to_equal(".examples-page h1", "Examples")
    assert len(dash_duo.find_elements(".example-card")) == 6
    dash_duo.wait_for_contains_class("#sidebar-link-examples", "active")
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.title == PAGE_METADATA["/examples"]["title"])
    assert dash_duo.driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth;")
    for example in EXAMPLES:
        dash_duo.driver.get(dash_duo.server_url + "/examples")
        link = dash_duo.wait_for_element(f"#example-{example['id']} .example-open")
        dash_duo.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
        WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.execute_script(
            "if (document.fonts.status !== 'loaded') return false;"
            "const element = arguments[0], rect = element.getBoundingClientRect();"
            "const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);"
            "return hit === element || element.contains(hit);", link,
        ))
        link.click()
        path = example["setup"]["page"]
        export_id = {"/experiment": "export-csv", "/single": "export-single-csv", "/population": "population-export"}[path]
        WebDriverWait(dash_duo.driver, 30).until(lambda driver: driver.find_element("id", export_id).is_enabled())
        assert dash_duo.driver.current_url.startswith(dash_duo.server_url + path + "?simulation=")
        if path == "/population":
            assert "mu_s" in dash_duo.find_element("#population-results").text
        else:
            graph_id = "result-graph" if path == "/experiment" else "single-graph"
            WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.execute_script(
                "const graph = document.querySelector('#' + arguments[0] + ' .js-plotly-plot');"
                "return graph && graph.data && graph.data.length > 0;", graph_id,
            ))
    assert dash_duo.get_logs() == []


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
        dash_duo.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        WebDriverWait(dash_duo.driver, 10).until(lambda driver: not any(
            option.is_displayed() for option in driver.find_elements("css selector", "#measure-select [role='option']")
        ))
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


def _shared_url(dash_duo, path, controls, plot_settings=None):
    from urllib.parse import urlencode
    from PyMieSimX.gui.sharing import encode_simulation
    token = encode_simulation({"v": 1, "page": path, "controls": controls, "plot_settings": plot_settings or {}})
    return dash_duo.server_url + path + "?" + urlencode({"simulation": token})


def _shared_field_id(section, name):
    from PyMieSimX.gui.sharing import control_key
    return control_key({"kind": "field", "section": section, "name": name})


def _copy_shared_link(dash_duo):
    dash_duo.driver.execute_cdp_cmd("Browser.grantPermissions", {
        "origin": dash_duo.server_url, "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"],
    })
    dash_duo.driver.execute_async_script(
        "const done = arguments[0], clipboard = navigator.clipboard || window.simulationTestClipboard;"
        "clipboard.writeText('').then(() => done(true), error => done(String(error)));"
    )
    clipboard = dash_duo.find_element("#simulation-clipboard")
    dash_duo.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clipboard)
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: driver.execute_script(
        "const element = arguments[0], rect = element.getBoundingClientRect();"
        "const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);"
        "return hit === element || element.contains(hit);", clipboard,
    ))
    initial_width = clipboard.rect["width"]
    clipboard.click()
    dash_duo.wait_for_text_to_equal("#simulation-clipboard", "✓ Copied")
    dash_duo.wait_for_contains_class("#simulation-clipboard", "simulation-copy-success")
    assert clipboard.rect["width"] == pytest.approx(initial_width, abs=1)
    def copied_link(driver):
        value = driver.execute_async_script(
            "const done = arguments[0], clipboard = navigator.clipboard || window.simulationTestClipboard;"
            "clipboard.readText().then(done, error => done(String(error)));"
        )
        return value if value.startswith(dash_duo.server_url + "/") and "?simulation=" in value else False
    link = WebDriverWait(dash_duo.driver, 10).until(copied_link)
    assert link.startswith(dash_duo.server_url + "/")
    assert "?simulation=" in link
    assert not dash_duo.driver.find_elements("css selector", "#simulation-share-link")
    assert not dash_duo.driver.find_elements("css selector", "#simulation-share-feedback, #simulation-link-fallback")
    dash_duo.wait_for_text_to_equal("#simulation-clipboard", "Copy simulation link")
    return link


@pytest.mark.parametrize("viewport", [(1440, 1000), (390, 844)], ids=["desktop", "mobile"])
def test_shared_sweep_restores_saved_inputs_and_runs_once(dash_duo, viewport, isolated_experiment_jobs, monkeypatch):
    from urllib.parse import urlsplit
    from PyMieSimX.gui.sharing import read_simulation
    dash_duo.driver.set_window_size(*viewport)
    submitted = []
    original_submit = isolated_experiment_jobs.submit

    def record_submit(**kwargs):
        submitted.append(kwargs)
        return original_submit(**kwargs)

    monkeypatch.setattr(isolated_experiment_jobs, "submit", record_submit)
    dash_duo.start_server(create_dash_app())
    controls = {
        "source-type": "PlaneWaveSet", "scatterer-type": "SphereSet", "detector-type": "None",
        "measure-select": ["Qsca", "Qext"], "x-axis-select": "diameter",
        _shared_field_id("source", "wavelength"): "600:700:3",
        _shared_field_id("scatterer", "diameter"): "80,120",
        _shared_field_id("scatterer", "material"): "main/SiO2/Malitson",
        "plot-experiment-font-size": 22, "plot-experiment-grid": False,
    }
    link = _shared_url(dash_duo, "/experiment", controls, {"font_size": 22, "show_grid": False, "template": "plotly_dark"})
    dash_duo.driver.get(link)
    dash_duo.wait_for_element(".simulation-link-notice")
    WebDriverWait(dash_duo.driver, 30).until(lambda _: dash_duo.find_element("#export-csv").is_enabled())
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: "diameter" in dash_duo.find_element("#x-axis-select").text)
    assert "Qsca" in dash_duo.find_element("#measure-select").text
    assert "Qext" in dash_duo.find_element("#measure-select").text
    assert len(submitted) == 1
    assert submitted[0]["source_values"]["wavelength"] == "600:700:3"
    assert submitted[0]["scatterer_values"]["diameter"] == "80,120"
    assert submitted[0]["measure"] == ["Qsca", "Qext"]
    copied_link = _copy_shared_link(dash_duo)
    restored = read_simulation(urlsplit(copied_link).query, "/experiment")
    assert restored["controls"].items() >= controls.items()
    assert restored["plot_settings"]["template"] == "plotly_dark"
    # Save a conflicting ordinary-session preference, then reopen the link.
    dash_duo.driver.get(dash_duo.server_url + "/experiment")
    dash_duo.wait_for_element("#experiment-tab-source").click()
    dash_duo.wait_for_contains_class("#experiment-right-sidebar", "open")
    _wait_for_sidebar_transition(dash_duo)
    field = dash_duo.driver.find_element("xpath", "//input[@id='" + _shared_field_id("source", "wavelength") + "']")
    field.clear()
    field.send_keys("777", Keys.TAB)
    WebDriverWait(dash_duo.driver, 10).until(lambda driver: field.get_attribute("value") == "777")
    dash_duo.driver.get(copied_link)
    dash_duo.wait_for_element("#simulation-clipboard")
    copied_again = _copy_shared_link(dash_duo)
    again = read_simulation(urlsplit(copied_again).query, "/experiment")
    assert again["controls"][_shared_field_id("source", "wavelength")] == "600:700:3"
    assert again["controls"]["measure-select"] == ["Qsca", "Qext"]
    assert dash_duo.driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth")
    WebDriverWait(dash_duo.driver, 30).until(lambda _: dash_duo.find_element("#export-csv").is_enabled())
    assert len(submitted) == 2
    assert dash_duo.get_logs() == []


def test_shared_single_setup_runs_once_with_restored_projection_and_remains_editable(dash_duo, monkeypatch):
    from urllib.parse import urlsplit
    from PyMieSimX.gui.sharing import read_simulation
    dash_duo.driver.set_window_size(1440, 1000)
    from PyMieSimX.gui import callbacks
    runs = []
    original_run = callbacks.execute_single_callback

    def record_run(**kwargs):
        runs.append(kwargs)
        return original_run(**kwargs)

    monkeypatch.setattr(callbacks, "execute_single_callback", record_run)
    dash_duo.start_server(create_dash_app())
    controls = {"single-source-type": "PlaneWave", "single-scatterer-type": "Sphere",
                "single-representation": "s1s2", "single-projection": "polar_1d", "single-sampling": "24",
                _shared_field_id("single-scatterer", "diameter"): "180",
                _shared_field_id("single-scatterer", "material"): "1.47+0.02j",
                "plot-single-font-size": 21, "plot-single-grid": False}
    dash_duo.driver.get(_shared_url(dash_duo, "/single", controls, {"font_size": 21, "show_grid": False}))
    dash_duo.wait_for_element(".simulation-link-notice")
    WebDriverWait(dash_duo.driver, 30).until(lambda _: dash_duo.find_element("#export-single-csv").is_enabled())
    assert len(runs) == 1
    assert runs[0]["projection"] == "polar_1d"
    assert runs[0]["sampling"] == "24"
    assert "180" in runs[0]["scatterer_values"]
    copied = read_simulation(urlsplit(_copy_shared_link(dash_duo)).query, "/single")
    assert copied["controls"].items() >= controls.items()
    dash_duo.find_element("#single-tab-plot-options").click()
    dash_duo.wait_for_contains_class("#single-right-sidebar", "open")
    _wait_for_sidebar_transition(dash_duo, "single-right-sidebar")
    font = dash_duo.find_element("#plot-single-font-size")
    font.clear()
    font.send_keys("25", Keys.TAB)
    dash_duo.select_dcc_dropdown("#single-projection", "2D plot")
    WebDriverWait(dash_duo.driver, 10, ignored_exceptions=(StaleElementReferenceException,)).until(
        lambda _: dash_duo.find_element("#plot-single-font-size").get_attribute("value") == "25"
    )
    dash_duo.find_element("#single-tab-plot-options").click()
    dash_duo.wait_for_class_to_equal("#single-right-sidebar", "right-sidebar-panel")
    _wait_for_sidebar_transition(dash_duo, "single-right-sidebar")
    assert len(runs) == 1
    dash_duo.find_element("#run-single-button").click()
    WebDriverWait(dash_duo.driver, 30).until(lambda _: len(runs) == 2 and dash_duo.find_element("#run-single-button").is_enabled())
    assert dash_duo.find_element("#export-single-csv").is_enabled()
    assert len(runs) == 2
    assert dash_duo.get_logs() == []


def test_shared_population_runs_with_restored_values_and_invalid_link_recovers(dash_duo, monkeypatch):
    from urllib.parse import urlsplit
    from PyMieSimX.gui.sharing import read_simulation
    dash_duo.driver.set_window_size(1440, 1000)
    from PyMieSimX.gui.pages import population
    runs = []
    original_compute = population.compute_population_optics

    def record_compute(**kwargs):
        runs.append(kwargs)
        return original_compute(**kwargs)

    monkeypatch.setattr(population, "compute_population_optics", record_compute)
    dash_duo.start_server(create_dash_app())
    controls = {"population-distribution": "gaussian", "population-width": "37",
                "population-diameter": "210", "population-concentration-basis": "volume",
                "population-concentration": "0.0023"}
    dash_duo.driver.get(_shared_url(dash_duo, "/population", controls))
    dash_duo.wait_for_element(".simulation-link-notice")
    dash_duo.wait_for_text_to_equal("#population-status", "Completed. All population properties are shown below.")
    copied = read_simulation(urlsplit(_copy_shared_link(dash_duo)).query, "/population")
    assert copied["controls"].items() >= controls.items()
    assert dash_duo.find_element("#population-export").is_enabled()
    assert len(runs) == 1
    assert runs[0]["width"] == "37"
    assert runs[0]["concentration"] == "0.0023"
    dash_duo.driver.get(dash_duo.server_url + "/experiment?simulation=broken")
    dash_duo.wait_for_element(".simulation-link-notice")
    assert "could not be read" in dash_duo.find_element(".simulation-link-notice").text
    assert dash_duo.find_element("#run-experiment-button").is_enabled()
    assert dash_duo.get_logs() == []


def test_simulation_link_available_without_clipboard_api(dash_duo):
    from urllib.parse import urlsplit
    from PyMieSimX.gui.sharing import read_simulation
    dash_duo.driver.set_window_size(1440, 1000)
    dash_duo.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "window.simulationTestClipboard = navigator.clipboard; Object.defineProperty(navigator, 'clipboard', {value: undefined});",
    })
    dash_duo.start_server(create_dash_app())
    dash_duo.find_element("#sidebar-link-single").click()
    link = _copy_shared_link(dash_duo)
    assert read_simulation(urlsplit(link).query, "/single")["page"] == "/single"
    assert not dash_duo.find_element("#export-single-csv").is_enabled()
    assert dash_duo.get_logs() == []


def test_copy_button_reports_failure_without_showing_a_card(dash_duo):
    dash_duo.driver.set_window_size(1440, 1000)
    dash_duo.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'clipboard', {value: {writeText: () => Promise.reject(new Error('denied'))}});"
                  "document.execCommand = () => false;",
    })
    dash_duo.start_server(create_dash_app())
    dash_duo.find_element("#sidebar-link-single").click()
    button = dash_duo.wait_for_element("#simulation-clipboard")
    button.click()
    dash_duo.wait_for_text_to_equal("#simulation-clipboard", "Unable to copy")
    dash_duo.wait_for_contains_class("#simulation-clipboard", "simulation-copy-error")
    assert not dash_duo.find_elements("#simulation-share-feedback, #simulation-share-link")
    dash_duo.wait_for_text_to_equal("#simulation-clipboard", "Copy simulation link")
    assert dash_duo.get_logs() == []


def test_shared_auto_run_validation_error_recovers_without_repeating(dash_duo, isolated_experiment_jobs):
    dash_duo.driver.set_window_size(1440, 1000)
    dash_duo.start_server(create_dash_app())
    link = _shared_url(dash_duo, "/experiment", {
        "source-type": "PlaneWaveSet", "scatterer-type": "SphereSet", "detector-type": "None",
        "measure-select": ["Qsca"], _shared_field_id("source", "wavelength"): "0",
    })
    dash_duo.driver.get(link)
    dash_duo.wait_for_element("#experiment-run-status .status-banner.error")
    assert "wavelength" in dash_duo.find_element("#experiment-run-status").text
    assert dash_duo.find_element("#run-experiment-button").is_enabled()
    assert not isolated_experiment_jobs._jobs
    dash_duo.find_element("#experiment-tab-source").click()
    dash_duo.wait_for_contains_class("#experiment-right-sidebar", "open")
    _wait_for_sidebar_transition(dash_duo)
    field = dash_duo.driver.find_element("xpath", "//input[@id='" + _shared_field_id("source", "wavelength") + "']")
    field.clear()
    field.send_keys("650", Keys.TAB)
    dash_duo.wait_for_no_elements("#source-fields .field-input-invalid")
    assert not isolated_experiment_jobs._jobs
    dash_duo.find_element("#experiment-tab-source").click()
    dash_duo.wait_for_class_to_equal("#experiment-right-sidebar", "right-sidebar-panel")
    _wait_for_sidebar_transition(dash_duo)
    dash_duo.find_element("#run-experiment-button").click()
    WebDriverWait(dash_duo.driver, 30).until(lambda _: dash_duo.find_element("#export-csv").is_enabled())
    assert len(isolated_experiment_jobs._jobs) == 1
    assert dash_duo.get_logs() == []
