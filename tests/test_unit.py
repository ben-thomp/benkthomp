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
