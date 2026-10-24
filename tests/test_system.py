"""System tests for end-to-end functionality."""


class TestEndToEnd:
    """System tests for the complete site."""

    def test_brand_link_returns_to_project_list(self, client):
        """Test that the site name links back to the project list."""
        html = client.get("/").data.decode()
        assert 'class="nav-brand"' in html
        assert 'href="/"' in html

    def test_page_uses_base_layout(self, client):
        """Test that the page has the navbar and stylesheet."""
        response = client.get("/")
        assert b"nav" in response.data.lower()
        assert b"style.css" in response.data
