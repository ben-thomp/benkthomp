"""System tests for end-to-end functionality."""


class TestEndToEndNavigation:
    """System tests for the complete navigation workflow."""

    def test_complete_navigation_workflow(self, client):
        """Test navigating through all pages."""
        # Step 1: Load the home page
        response = client.get("/")
        assert response.status_code == 200
        assert b"benkthomp" in response.data

        # Step 2: Navigate to about
        response = client.get("/about")
        assert response.status_code == 200
        assert b"About" in response.data

        # Step 3: Navigate to projects
        response = client.get("/projects")
        assert response.status_code == 200
        assert b"Projects" in response.data

        # Step 4: Navigate to contact
        response = client.get("/contact")
        assert response.status_code == 200
        assert b"Contact" in response.data

    def test_all_pages_share_base_layout(self, client):
        """Test that all pages use the base template with navbar."""
        pages = ["/", "/about", "/projects", "/contact"]

        for page in pages:
            response = client.get(page)
            assert response.status_code == 200
            assert response.content_type.startswith("text/html")
            # All pages should have the navbar
            assert b"nav" in response.data.lower()
            # All pages should link to the stylesheet
            assert b"style.css" in response.data
