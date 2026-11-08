"""Integration tests for the /roadmap page built from project ROADMAP.md files."""

import benkthomp.github as gh

README = """# demo

A small demo project.

## Roadmap

- [ ] Ship the thing
- [x] Write the plan

### Backlog

- Later idea

## Decisions

- **Flask**: simple
"""
LEGACY = """# demo

## Status

Ongoing development.

## Next Up

- [ ] Ship the legacy thing

## Milestones

- [x] v0.1 — first release
"""


class TestRoadmapPage:
    def test_lists_repo_projects_without_a_roadmap(self, client):
        response = client.get("/roadmap")
        assert response.status_code == 200
        assert b"python-notes" in response.data
        assert b"No roadmap published yet." in response.data

    def test_shows_current_work_from_the_readme_without_status(
        self, client, monkeypatch
    ):
        files = {"README.md": README}
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: files.get(path))
        data = client.get("/roadmap").data
        assert b"Ship the thing" in data and b"Write the plan" in data
        assert b"Later idea" not in data and b"Flask" not in data
        assert b"Status" not in data and b"Milestones" not in data

    def test_falls_back_to_roadmap_md_and_hides_its_status(self, client, monkeypatch):
        files = {"ROADMAP.md": LEGACY}
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: files.get(path))
        data = client.get("/roadmap").data
        assert b"Ship the legacy thing" in data
        assert b"Ongoing development." not in data
        assert b"v0.1" not in data

    def test_site_pages_without_a_repo_are_not_listed(self, client):
        data = client.get("/roadmap").data
        assert b"Gregory" not in data
        assert b"Roxy" not in data

    def test_names_link_to_project_pages(self, client):
        data = client.get("/roadmap").data
        assert b'href="/projects/python-notes"' in data
