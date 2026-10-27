"""Integration tests for the /roadmap page built from project ROADMAP.md files."""

import benkthomp.project_roadmap as pr

ROADMAP = """# demo

## Status

Ongoing development.

## Next Up

- [ ] Ship the thing

## Milestones

- [x] v0.1 — first release
"""


class TestRoadmapPage:
    def test_lists_repo_projects_without_a_roadmap(self, client):
        response = client.get("/roadmap")
        assert response.status_code == 200
        assert b"python-notes" in response.data
        assert b"No roadmap published yet." in response.data

    def test_shows_status_next_up_and_milestones(self, client, monkeypatch):
        monkeypatch.setattr(pr, "_fetch_text", lambda repo: ROADMAP)
        data = client.get("/roadmap").data
        assert b"Ongoing development." in data
        assert b"Ship the thing" in data
        assert b"v0.1" in data

    def test_site_pages_without_a_repo_are_not_listed(self, client):
        data = client.get("/roadmap").data
        assert b"Gregory" not in data
        assert b"Roxy" not in data
