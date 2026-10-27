"""Integration tests for /projects/<repo> pages."""

import benkthomp.github as gh

README = "# Notes\n\nA notes app. See [docs](docs/a.md).\n"
ROADMAP = "# notes\n\n## Status\n\nOngoing.\n\n## Next Up\n\n- [ ] Ship it\n"
TREE = [
    {"path": "src", "type": "tree"},
    {"path": "src/app.py", "type": "blob"},
    {"path": "README.md", "type": "blob"},
]


def _fake_fetch(repo, path):
    return {"README.md": README, "ROADMAP.md": ROADMAP}.get(path)


class TestProjectPage:
    def test_renders_readme_tree_and_roadmap(self, client, monkeypatch):
        monkeypatch.setattr(gh, "_fetch_text", _fake_fetch)
        monkeypatch.setattr(gh, "_fetch_tree", lambda repo: TREE)
        response = client.get("/projects/python-notes")
        assert response.status_code == 200
        data = response.data
        assert b"<h1>Notes</h1>" in data
        assert b"Ongoing." in data and b"Ship it" in data
        assert b"app.py" in data
        assert b"https://github.com/ben-thomp/python-notes/blob/HEAD/src/app.py" in data
        assert b"View on GitHub" in data

    def test_degrades_gracefully_without_github(self, client):
        response = client.get("/projects/python-notes")
        assert response.status_code == 200
        assert b"No roadmap published yet." in response.data
        assert b"File list unavailable" in response.data
        assert b"No README yet." in response.data

    def test_unknown_repo_is_404(self, client):
        assert client.get("/projects/not-a-listed-repo").status_code == 404

    def test_site_page_names_are_not_repo_pages(self, client):
        assert client.get("/projects/gregory").status_code == 404
