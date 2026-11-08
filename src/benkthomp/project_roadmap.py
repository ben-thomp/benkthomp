"""Per-project roadmaps, read from each repo's README and cached.

A README with a `## Roadmap` section is the source. Items directly under that
heading are current work, an optional `### Backlog` subsection holds later work,
and a top-level `## Decisions` section lists decisions. Repos that haven't moved
over still have a ROADMAP.md, which is the fallback: its Next Up becomes the
current list. Remove the fallback once every project has moved.

The site reads public repos only, through the cached GitHub module.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from benkthomp import github
from benkthomp.projects import PROJECTS

_ITEM = re.compile(r"^\s*[-*]\s*(\[(?P<box>[ xX])\])?\s*(?P<text>.*)$")
_ROADMAP_HEADING = re.compile(r"^##\s+roadmap\s*$", re.IGNORECASE | re.MULTILINE)
_README_SECTIONS = {"roadmap": "current", "decisions": "decisions"}
_LEGACY_SECTIONS = {
    "next up": "current",
    "backlog": "backlog",
    "decisions": "decisions",
}


def _empty() -> dict[str, Any]:
    return {"title": "", "summary": "", "current": [], "backlog": [], "decisions": []}


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _item(line: str) -> dict[str, Any] | None:
    """Parses a bullet into {"text", "done"} (done is None without a checkbox)."""
    match = _ITEM.match(line)
    if not match or not match.group("text").strip():
        return None
    box = match.group("box")
    return {
        "text": match.group("text").strip(),
        "done": None if box is None else box.lower() == "x",
    }


def _title_and_summary(lines: list[str]) -> tuple[str, str]:
    """Returns the first `# ` title and the paragraph directly after it."""
    in_fence = False
    title_at = -1
    for position, line in enumerate(lines):
        if _is_fence(line):
            in_fence = not in_fence
        elif line.startswith("# ") and not in_fence:
            title_at = position
            break
    if title_at < 0:
        return "", ""
    summary: list[str] = []
    for line in lines[title_at + 1 :]:
        text = line.strip()
        if not text:
            if summary:
                break
        elif text.startswith(("#", "---")):
            break
        elif not text.startswith(("![", "[![", "<")):  # skip badges and raw HTML
            summary.append(text)
    return lines[title_at][2:].strip(), " ".join(summary)


def parse_readme(text: str) -> dict[str, Any]:
    """Parses a README's `## Roadmap` and `## Decisions` sections.

    Items are {"text", "done"} (done is None when the item has no checkbox).
    Bullets under `## Roadmap` are current work and those under `### Backlog`
    are later work; other `###` subsections are ignored. The summary is the
    first paragraph after the title, so Setup and Usage text stays out of it.
    """
    lines = text.splitlines()
    result = _empty()
    result["title"], result["summary"] = _title_and_summary(lines)
    section: str | None = None
    in_roadmap = False
    in_fence = False
    for line in lines:
        if _is_fence(line):
            in_fence = not in_fence
        elif in_fence:
            continue
        elif line.startswith("## "):
            name = line[3:].strip().lower()
            in_roadmap = name == "roadmap"
            section = _README_SECTIONS.get(name)
        elif line.startswith("### ") and in_roadmap:
            backlog = line[4:].strip().lower() == "backlog"
            section = "backlog" if backlog else None
        elif section:
            item = _item(line)
            if item:
                result[section].append(item)
    return result


def parse_legacy_roadmap(text: str) -> dict[str, Any]:
    """Parses a ROADMAP.md: its Next Up becomes the current list.

    Status and Milestones are not part of the new layout and are dropped.
    """
    lines = text.splitlines()
    result = _empty()
    result["title"], result["summary"] = _title_and_summary(lines)
    section: str | None = None
    for line in lines:
        if line.startswith("## "):
            section = _LEGACY_SECTIONS.get(line[3:].strip().lower())
        elif section:
            item = _item(line)
            if item:
                result[section].append(item)
    return result


def strip_roadmap_sections(readme: str) -> str:
    """Removes `## Roadmap` and `## Decisions` from README text.

    The site shows the roadmap in its own block, so it isn't repeated in the
    rendered README. Text is returned unchanged if there is no Roadmap section.
    """
    if not _ROADMAP_HEADING.search(readme):
        return readme
    kept: list[str] = []
    skipping = False
    in_fence = False
    for line in readme.splitlines():
        if _is_fence(line):
            in_fence = not in_fence
        elif line.startswith("## ") and not in_fence:
            skipping = line[3:].strip().lower() in _README_SECTIONS
        if not skipping:
            kept.append(line)
    return "\n".join(kept) + "\n"


def get_roadmap(repo: str) -> dict[str, Any] | None:
    """Returns the parsed roadmap for a repo, or None if unavailable.

    Reads the README's `## Roadmap` section, or falls back to ROADMAP.md.
    """
    readme = github.get_text(repo, "README.md")
    if readme is not None and _ROADMAP_HEADING.search(readme):
        return parse_readme(readme)
    legacy = github.get_text(repo, "ROADMAP.md")
    return None if legacy is None else parse_legacy_roadmap(legacy)


def get_all() -> list[dict[str, Any]]:
    """Returns {"project", "roadmap"} for every project with a GitHub repo."""
    projects = [p for p in PROJECTS if "repo" in p]
    with ThreadPoolExecutor(max_workers=8) as pool:
        roadmaps = list(pool.map(lambda p: get_roadmap(p["repo"]), projects))
    return [{"project": p, "roadmap": r} for p, r in zip(projects, roadmaps)]
