"""Small browser-level smoke suite for the critical dashboard workflow."""

from PyMieSimX.gui.interface import create_dash_app


def test_navigation_validation_execution_plot_and_export_controls(dash_duo):
    dash_duo.start_server(create_dash_app())
    dash_duo.wait_for_text_to_equal("h1", "PyMieSim")
    assert dash_duo.find_elements(".home-metric-value") == []

    dash_duo.find_element("#sidebar-link-experiment").click()
    dash_duo.wait_for_element("#result-graph")
    dash_duo.wait_for_element("#export-csv")
    dash_duo.wait_for_element("#experiment-tab-source").click()
    dash_duo.wait_for_element("#source-fields .field-input")

    field = dash_duo.find_element("#source-fields .field-input")
    field.clear()
    field.send_keys("-1")
    field.send_keys("\ue007")
    dash_duo.wait_for_element("#source-fields .field-input-invalid")

    dash_duo.find_element("#sidebar-link-single").click()
    dash_duo.wait_for_element("#single-graph .plotly")
    dash_duo.wait_for_element("#export-single-csv")
