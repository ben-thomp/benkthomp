"""Unit tests for benkthomp application."""

from benkthomp.app import create_app


class TestAppFactory:
    """Unit tests for the application factory."""

    def test_create_app_returns_flask_instance(self):
        """Test that create_app returns a Flask app."""
        app = create_app()
        assert app is not None
        assert app.name == "benkthomp.app"

    def test_create_app_with_testing_config(self):
        """Test that config overrides are applied."""
        app = create_app(config={"TESTING": True})
        assert app.config["TESTING"] is True

    def test_create_app_default_secret_key(self):
        """Test that a default secret key is set."""
        app = create_app()
        assert app.config["SECRET_KEY"] is not None


class TestProjects:
    """Unit tests for project data."""

    def test_projects_have_required_fields(self):
        """Test that every project has the fields the template uses."""
        from benkthomp.projects import PROJECTS

        for project in PROJECTS:
            assert {"name", "description", "language"} <= project.keys()

    def test_project_url(self):
        """Test that project URLs point at the GitHub repo."""
        from benkthomp.projects import project_url

        assert project_url({"name": "x"}) == "https://github.com/ben-thomp/x"
