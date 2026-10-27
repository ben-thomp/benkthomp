"""Unit tests for the app factory."""

from benkthomp.app import create_app


class TestAppFactory:
    def test_create_app_returns_flask_instance(self):
        app = create_app()
        assert app is not None
        assert app.name == "benkthomp.app"

    def test_create_app_with_testing_config(self):
        app = create_app(config={"TESTING": True})
        assert app.config["TESTING"] is True

    def test_create_app_default_secret_key(self):
        app = create_app()
        assert app.config["SECRET_KEY"] is not None
