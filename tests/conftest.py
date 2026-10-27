"""Pytest configuration and fixtures."""

import shutil

import pytest

from benkthomp.app import create_app


@pytest.fixture(autouse=True)
def enclosure_db(tmp_path, monkeypatch):
    """Point enclosure storage at a throwaway DB with a known ingest token."""
    monkeypatch.setenv("ENCLOSURE_DB_PATH", str(tmp_path / "enclosures.db"))
    monkeypatch.setenv("ENCLOSURE_INGEST_TOKEN", "test-token")


@pytest.fixture(autouse=True)
def no_network_github(monkeypatch):
    """Keep GitHub-backed pages off the network and cache-free."""
    import benkthomp.github as gh

    gh.clear_cache()
    monkeypatch.delenv("PROJECTS_LOCAL_DIR", raising=False)
    monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: None)
    monkeypatch.setattr(gh, "_fetch_tree", lambda repo: None)
    yield
    gh.clear_cache()


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
