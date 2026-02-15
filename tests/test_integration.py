"""Integration tests for Flask routes."""


class TestHomeRoute:
    """Integration tests for the home page."""

    def test_home_route_exists(self, client):
        """Test that the home route is accessible."""
        response = client.get("/")
        assert response.status_code == 200

    def test_home_route_returns_html(self, client):
        """Test that the home route returns HTML content."""
        response = client.get("/")
        assert response.content_type.startswith("text/html")

    def test_home_page_contains_site_name(self, client):
        """Test that the home page contains the site name."""
        response = client.get("/")
        assert b"benkthomp" in response.data


class TestAboutRoute:
    """Integration tests for the about page."""

    def test_about_route_exists(self, client):
        """Test that the about route is accessible."""
        response = client.get("/about")
        assert response.status_code == 200

    def test_about_route_returns_html(self, client):
        """Test that the about route returns HTML content."""
        response = client.get("/about")
        assert response.content_type.startswith("text/html")

    def test_about_page_contains_heading(self, client):
        """Test that the about page contains the About heading."""
        response = client.get("/about")
        assert b"About" in response.data


class TestProjectsRoute:
    """Integration tests for the projects page."""

    def test_projects_route_exists(self, client):
        """Test that the projects route is accessible."""
        response = client.get("/projects")
        assert response.status_code == 200

    def test_projects_route_returns_html(self, client):
        """Test that the projects route returns HTML content."""
        response = client.get("/projects")
        assert response.content_type.startswith("text/html")

    def test_projects_page_contains_heading(self, client):
        """Test that the projects page contains the Projects heading."""
        response = client.get("/projects")
        assert b"Projects" in response.data


class TestContactRoute:
    """Integration tests for the contact page."""

    def test_contact_route_exists(self, client):
        """Test that the contact route is accessible."""
        response = client.get("/contact")
        assert response.status_code == 200

    def test_contact_route_returns_html(self, client):
        """Test that the contact route returns HTML content."""
        response = client.get("/contact")
        assert response.content_type.startswith("text/html")

    def test_contact_page_contains_heading(self, client):
        """Test that the contact page contains the Contact heading."""
        response = client.get("/contact")
        assert b"Contact" in response.data


class TestStaticFiles:
    """Integration tests for static file serving."""

    def test_static_css_accessible(self, client):
        """Test that CSS files are accessible."""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
