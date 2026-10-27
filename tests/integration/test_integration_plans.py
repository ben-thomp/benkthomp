"""Integration tests for the enclosure plan drawings on Roxy's page."""

import re
import xml.etree.ElementTree as ET

import pytest

from benkthomp import enclosures

FIGURES = [fig["file"] for fig in enclosures.SUBJECTS["roxy"]["plans"]["figures"]]


class TestRoxyPlans:
    def test_roxy_page_has_monitoring_and_plans_tabs(self, client):
        data = client.get("/roxy").data
        assert b'data-panel="monitoring"' in data
        assert b"6x2x2 Enclosure" in data
        assert b'id="panel-plans"' in data

    def test_gregory_page_has_no_tabs(self, client):
        data = client.get("/gregory").data
        assert b'role="tablist"' not in data
        assert b'id="panel-plans"' not in data

    @pytest.mark.parametrize("figure", FIGURES)
    def test_every_figure_is_wellformed_svg_with_title_and_desc(self, client, figure):
        html = client.get("/roxy").get_data(as_text=True)
        svgs = re.findall(r"<svg.*?</svg>", html, flags=re.DOTALL)
        assert len(svgs) == len(FIGURES)
        root = ET.fromstring(svgs[FIGURES.index(figure)])
        ns = "{http://www.w3.org/2000/svg}"
        assert root.find(f"{ns}title") is not None
        assert root.find(f"{ns}desc") is not None

    def test_figures_have_no_scripts_or_external_references(self, client):
        html = client.get("/roxy").get_data(as_text=True)
        for svg in re.findall(r"<svg.*?</svg>", html, flags=re.DOTALL):
            assert "<script" not in svg
            assert "http" not in svg.replace("http://www.w3.org/2000/svg", "")

    def test_marker_ids_are_unique_on_the_page(self, client):
        html = client.get("/roxy").get_data(as_text=True)
        ids = re.findall(r'\bid="([^"]+)"', html)
        assert len(ids) == len(set(ids))
