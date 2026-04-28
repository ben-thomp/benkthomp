"""Pytest configuration and fixtures."""

import shutil

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


@pytest.fixture
def roadmap_client(client, tmp_path, monkeypatch):
    from ruamel.yaml import YAML

    import benkthomp.roadmap as rm

    progress_file = tmp_path / "roadmap_progress.yaml"
    shutil.copy(rm._TEMPLATE_FILE, progress_file)
    y = YAML()
    y.preserve_quotes = True
    with open(progress_file, encoding="utf-8") as f:
        data = y.load(f)
    data["certs"]["genai"]["config"]["start"] = "2026-04-20"
    data["certs"]["genai"]["config"]["exam"] = "2026-06-12"
    data["certs"]["cpcu555"]["config"]["start"] = "2026-06-19"
    data["certs"]["cpcu555"]["config"]["exam"] = "2026-07-15"
    with open(progress_file, "w", encoding="utf-8") as f:
        y.dump(data, f)
    monkeypatch.setattr(rm, "_INSTANCE_DIR", tmp_path)
    monkeypatch.setattr(rm, "_PROGRESS_FILE", progress_file)
    return client
