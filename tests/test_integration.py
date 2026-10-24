"""Integration tests for Flask routes."""

from benkthomp.projects import GITHUB_URL, PROJECTS


class TestIndexRoute:
    """Integration tests for the project list page."""

    def test_index_route_exists(self, client):
        """Test that the index route is accessible."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_route_returns_html(self, client):
        """Test that the index route returns HTML content."""
        response = client.get("/")
        assert response.content_type.startswith("text/html")

    def test_index_lists_every_project(self, client):
        """Test that each project is rendered with a link to its repo."""
        html = client.get("/").data.decode()
        for project in PROJECTS:
            assert project["name"] in html
            assert f"{GITHUB_URL}/{project['name']}" in html

    def test_index_links_to_github_profile(self, client):
        """Test that the nav links to the GitHub profile."""
        assert GITHUB_URL.encode() in client.get("/").data

    def test_removed_pages_return_404(self, client):
        """Test that the old pages no longer exist."""
        for path in ["/about", "/projects", "/contact"]:
            assert client.get(path).status_code == 404


class TestStaticFiles:
    """Integration tests for static file serving."""

    def test_static_css_accessible(self, client):
        """Test that CSS files are accessible."""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
