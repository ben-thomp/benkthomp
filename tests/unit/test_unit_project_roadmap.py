"""Unit tests for ROADMAP.md parsing, caching and fallback."""

import benkthomp.project_roadmap as pr

# Captured at import, before the autouse fixture stubs it out.
REAL_FETCH_TEXT = pr._fetch_text

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

    def test_caches_within_ttl(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            pr, "_fetch_text", lambda repo: calls.append(repo) or SAMPLE
        )
        pr.get_roadmap("demo")
        pr.get_roadmap("demo")
        assert calls == ["demo"]

    def test_keeps_last_good_copy_when_refresh_fails(self, monkeypatch):
        monkeypatch.setattr(pr, "_fetch_text", lambda repo: SAMPLE)
        first = pr.get_roadmap("demo")
        pr._cache["demo"] = (0.0, first)  # force expiry
        monkeypatch.setattr(pr, "_fetch_text", lambda repo: None)
        assert pr.get_roadmap("demo") == first

    def test_local_dir_override(self, tmp_path, monkeypatch):
        (tmp_path / "demo").mkdir()
        (tmp_path / "demo" / "ROADMAP.md").write_text(SAMPLE, encoding="utf-8")
        monkeypatch.setattr(pr, "_fetch_text", REAL_FETCH_TEXT)
        monkeypatch.setenv("PROJECT_ROADMAP_LOCAL_DIR", str(tmp_path))
        pr.clear_cache()
        assert pr.get_roadmap("demo")["title"] == "demo"
        assert pr.get_roadmap("absent") is None
