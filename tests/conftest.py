"""Pytest configuration and fixtures."""

import pytest

from benkthomp.app import create_app


@pytest.fixture
def app():
    """Create and configure a test Flask app instance."""
    app = create_app(config={"TESTING": True, "SECRET_KEY": "test-secret-key"})
    yield app


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()
