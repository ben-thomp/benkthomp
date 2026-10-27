"""Unit tests for ROADMAP.md parsing, caching and fallback."""

import benkthomp.github as gh
import benkthomp.project_roadmap as pr

SAMPLE = """# demo

A small demo project.

---

## Status

Ongoing development.
No defined end state.

## Next Up

- [ ] Ship the thing
- [x] Write the plan

## Backlog

-

## Milestones

- [ ] v1.0 — replaces Notion
- Plain bullet

## Decisions

- **Flask** — simple
"""


class TestParseRoadmap:
    def test_title_summary_and_status(self):
        parsed = pr.parse_roadmap(SAMPLE)
        assert parsed["title"] == "demo"
        assert parsed["summary"] == "A small demo project."
        assert parsed["status"] == "Ongoing development. No defined end state."

    def test_checkboxes_and_plain_bullets(self):
        parsed = pr.parse_roadmap(SAMPLE)
        assert parsed["next_up"] == [
            {"text": "Ship the thing", "done": False},
            {"text": "Write the plan", "done": True},
        ]
        assert parsed["milestones"][1] == {"text": "Plain bullet", "done": None}

    def test_empty_bullets_are_dropped(self):
        assert pr.parse_roadmap(SAMPLE)["backlog"] == []

    def test_unknown_sections_and_empty_text_are_safe(self):
        parsed = pr.parse_roadmap("# x\n\n## Random\n\n- ignored\n")
        assert parsed["next_up"] == []
        assert pr.parse_roadmap("")["title"] == ""


class TestGetRoadmap:
    def test_returns_none_when_unavailable(self):
        assert pr.get_roadmap("missing") is None

    def test_parses_fetched_text(self, monkeypatch):
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: SAMPLE)
        assert pr.get_roadmap("demo")["title"] == "demo"

    def test_only_projects_with_a_repo_are_listed(self):
        names = [e["project"]["name"] for e in pr.get_all()]
        assert "python-notes" in names
        assert "Gregory" not in names
