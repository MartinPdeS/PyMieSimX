"""Search metadata is available before JavaScript renders the application."""

from html.parser import HTMLParser

import pytest

from PyMieSimX.gui.interface import create_dash_app
from PyMieSimX.gui.seo import PAGE_METADATA


class HeadParser(HTMLParser):
    """Collect titles and descriptions without assuming HTML attribute order."""

    def __init__(self):
        super().__init__()
        self.in_title = False
        self.titles = []
        self.descriptions = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "description":
            self.descriptions.append(attributes.get("content"))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.titles.append(data)


@pytest.fixture(scope="module")
def client():
    return create_dash_app().server.test_client()


@pytest.mark.parametrize("path", PAGE_METADATA)
def test_direct_requests_have_unique_page_metadata(client, path):
    response = client.get(path)
    assert response.status_code == 200
    parser = HeadParser()
    parser.feed(response.get_data(as_text=True))
    assert parser.titles == [PAGE_METADATA[path]["title"]]
    assert parser.descriptions == [PAGE_METADATA[path]["description"]]


def test_query_parameters_do_not_leak_into_head_metadata(client):
    response = client.get('/single?input=%22%3E%3Cscript%3Euntrusted%3C/script%3E')
    parser = HeadParser()
    parser.feed(response.get_data(as_text=True))
    assert parser.titles == [PAGE_METADATA["/single"]["title"]]
    assert parser.descriptions == [PAGE_METADATA["/single"]["description"]]

