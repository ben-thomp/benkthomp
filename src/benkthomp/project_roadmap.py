"""Per-project roadmaps, read from each repo's ROADMAP.md and cached.

Each repo keeps a ROADMAP.md with the sections Status, Next Up, Backlog,
Milestones and Decisions. The site reads those files (public repos only) via
the cached GitHub module and parses them.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from benkthomp import github
from benkthomp.projects import PROJECTS

_SECTIONS = {
    "status": "status",
    "next up": "next_up",
    "backlog": "backlog",
    "milestones": "milestones",
    "decisions": "decisions",
}
_ITEM = re.compile(r"^\s*[-*]\s*(\[(?P<box>[ xX])\])?\s*(?P<text>.*)$")


def parse_roadmap(text: str) -> dict[str, Any]:
    """Parses ROADMAP.md text into title, summary and the five known sections.

    List sections become lists of {"text", "done"} (done is None when the item
    has no checkbox). Status stays as plain text. Empty bullets are dropped.
    """
    result: dict[str, Any] = {
        "title": "",
        "summary": "",
        "status": "",
        "next_up": [],
        "backlog": [],
        "milestones": [],
        "decisions": [],
    }
    section: str | None = None
    summary: list[str] = []
    status: list[str] = []
    for line in text.splitlines():
        if line.startswith("# ") and not result["title"]:
            result["title"] = line[2:].strip()
        elif line.startswith("## "):
            section = _SECTIONS.get(line[3:].strip().lower())
        elif line.strip() == "---":
            continue
        elif section is None:
            if result["title"] and line.strip():
                summary.append(line.strip())
        elif section == "status":
            if line.strip():
                status.append(line.strip())
        else:
            match = _ITEM.match(line)
            if match and match.group("text").strip():
                box = match.group("box")
                result[section].append(
                    {
                        "text": match.group("text").strip(),
                        "done": None if box is None else box.lower() == "x",
                    }
                )
    result["summary"] = " ".join(summary)
    result["status"] = " ".join(status)
    return result


def get_roadmap(repo: str) -> dict[str, Any] | None:
    """Returns the parsed ROADMAP.md for a repo, or None if unavailable."""
    text = github.get_text(repo, "ROADMAP.md")
    return None if text is None else parse_roadmap(text)


def get_all() -> list[dict[str, Any]]:
    """Returns {"project", "roadmap"} for every project with a GitHub repo."""
    projects = [p for p in PROJECTS if "repo" in p]
    with ThreadPoolExecutor(max_workers=8) as pool:
        roadmaps = list(pool.map(lambda p: get_roadmap(p["repo"]), projects))
    return [{"project": p, "roadmap": r} for p, r in zip(projects, roadmaps)]
