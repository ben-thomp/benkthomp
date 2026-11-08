"""Unit tests for roadmap parsing (README and ROADMAP.md), caching and fallback."""

import benkthomp.github as gh
import benkthomp.project_roadmap as pr

README = """# demo

[![badge](https://example.com/b.svg)](https://example.com)

A small demo project.
It has two lines.

Second paragraph is not the summary.

## Setup

```bash
## not a heading
pip install demo
```

- a bullet in Setup that must be ignored

## Roadmap

- [ ] Ship the thing
- [x] Write the plan
- Plain bullet
-

### Backlog

- Later idea
- [ ] Another idea

### Notes

- ignored subsection bullet

## Decisions

- **Flask**: simple

## License

MIT
"""

LEGACY = """# demo

A small demo project.

---

## Status

Ongoing development.

## Next Up

- [ ] Ship the thing
- [x] Write the plan

## Backlog

- Later idea

## Milestones

- [ ] v1.0 — replaces Notion

## Decisions

- **Flask** — simple
"""


class TestParseReadme:
    def test_title_and_summary_from_first_paragraph_only(self):
        parsed = pr.parse_readme(README)
        assert parsed["title"] == "demo"
        assert parsed["summary"] == "A small demo project. It has two lines."

    def test_current_items_are_directly_under_roadmap(self):
        assert pr.parse_readme(README)["current"] == [
            {"text": "Ship the thing", "done": False},
            {"text": "Write the plan", "done": True},
            {"text": "Plain bullet", "done": None},
        ]

    def test_backlog_is_a_roadmap_subsection(self):
        assert pr.parse_readme(README)["backlog"] == [
            {"text": "Later idea", "done": None},
            {"text": "Another idea", "done": False},
        ]

    def test_decisions_is_a_top_level_section(self):
        assert pr.parse_readme(README)["decisions"] == [
            {"text": "**Flask**: simple", "done": None}
        ]

    def test_other_sections_and_code_fences_are_ignored(self):
        parsed = pr.parse_readme(README)
        texts = [i["text"] for key in ("current", "backlog") for i in parsed[key]]
        assert "a bullet in Setup that must be ignored" not in texts
        assert "ignored subsection bullet" not in texts

    def test_empty_text_and_missing_sections_are_safe(self):
        assert pr.parse_readme("")["title"] == ""
        parsed = pr.parse_readme("# x\n\n## Usage\n\n- ignored\n")
        assert parsed["current"] == [] and parsed["decisions"] == []

    def test_no_status_key(self):
        assert "status" not in pr.parse_readme(README)


class TestParseLegacyRoadmap:
    def test_next_up_becomes_current_and_status_is_dropped(self):
        parsed = pr.parse_legacy_roadmap(LEGACY)
        assert parsed["current"] == [
            {"text": "Ship the thing", "done": False},
            {"text": "Write the plan", "done": True},
        ]
        assert "status" not in parsed and "milestones" not in parsed

    def test_summary_backlog_and_decisions(self):
        parsed = pr.parse_legacy_roadmap(LEGACY)
        assert parsed["summary"] == "A small demo project."
        assert parsed["backlog"] == [{"text": "Later idea", "done": None}]
        assert parsed["decisions"][0]["text"] == "**Flask** — simple"

    def test_unknown_sections_are_safe(self):
        parsed = pr.parse_legacy_roadmap("# x\n\n## Random\n\n- ignored\n")
        assert parsed["current"] == []


class TestStripRoadmapSections:
    def test_removes_roadmap_backlog_and_decisions_only(self):
        stripped = pr.strip_roadmap_sections(README)
        assert "## Roadmap" not in stripped and "Ship the thing" not in stripped
        assert "Later idea" not in stripped and "## Decisions" not in stripped
        assert "## Setup" in stripped and "pip install demo" in stripped
        assert "## License" in stripped

    def test_unchanged_without_a_roadmap_section(self):
        text = "# x\n\n## Decisions\n\n- keep me\n"
        assert pr.strip_roadmap_sections(text) == text


class TestGetRoadmap:
    def test_returns_none_when_unavailable(self):
        assert pr.get_roadmap("missing") is None

    def test_reads_the_readme_roadmap_section(self, monkeypatch):
        monkeypatch.setattr(
            gh,
            "_fetch_text",
            lambda repo, path: README if path == "README.md" else None,
        )
        assert pr.get_roadmap("demo")["current"][0]["text"] == "Ship the thing"

    def test_readme_wins_over_roadmap_md(self, monkeypatch):
        files = {"README.md": README, "ROADMAP.md": LEGACY}
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: files.get(path))
        assert pr.get_roadmap("demo")["backlog"][0]["text"] == "Later idea"
        assert len(pr.get_roadmap("demo")["current"]) == 3

    def test_falls_back_to_roadmap_md_without_a_roadmap_section(self, monkeypatch):
        files = {"README.md": "# demo\n\n## Usage\n\nRun it.\n", "ROADMAP.md": LEGACY}
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: files.get(path))
        assert len(pr.get_roadmap("demo")["current"]) == 2

    def test_falls_back_when_the_readme_is_missing(self, monkeypatch):
        files = {"ROADMAP.md": LEGACY}
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: files.get(path))
        assert pr.get_roadmap("demo")["title"] == "demo"

    def test_none_when_readme_has_no_roadmap_and_no_roadmap_md(self, monkeypatch):
        files = {"README.md": "# demo\n\nJust a readme.\n"}
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: files.get(path))
        assert pr.get_roadmap("demo") is None

    def test_only_projects_with_a_repo_are_listed(self):
        names = [e["project"]["name"] for e in pr.get_all()]
        assert "python-notes" in names
        assert "Gregory" not in names
