"""Per-project roadmaps, read from each repo's ROADMAP.md and cached.

Each repo keeps a ROADMAP.md with the sections Status, Next Up, Backlog,
Milestones and Decisions. The site fetches those files (public repos only),
parses them, and keeps the last good copy if GitHub is unreachable.
"""

import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from benkthomp.projects import GITHUB_USER, PROJECTS

CACHE_TTL_SECONDS = 3600
FETCH_TIMEOUT_SECONDS = 5

_RAW_URL = "https://raw.githubusercontent.com/{user}/{repo}/HEAD/ROADMAP.md"
_SECTIONS = {
    "status": "status",
    "next up": "next_up",
    "backlog": "backlog",
    "milestones": "milestones",
    "decisions": "decisions",
}
_ITEM = re.compile(r"^\s*[-*]\s*(\[(?P<box>[ xX])\])?\s*(?P<text>.*)$")

# repo -> (fetched_at, parsed roadmap or None)
_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}


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


def _fetch_text(repo: str) -> str | None:
    """Returns a repo's ROADMAP.md text, or None if unavailable."""
    local_dir = os.environ.get("PROJECT_ROADMAP_LOCAL_DIR")
    if local_dir:
        path = Path(local_dir) / repo / "ROADMAP.md"
        return path.read_text(encoding="utf-8") if path.is_file() else None
    url = _RAW_URL.format(user=GITHUB_USER, repo=repo)
    try:
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError):
        return None


def get_roadmap(repo: str) -> dict[str, Any] | None:
    """Returns the parsed roadmap for a repo, cached for CACHE_TTL_SECONDS.

    If a refresh fails, the previous copy (if any) is kept and retried later.
    """
    now = time.monotonic()
    cached = _cache.get(repo)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    text = _fetch_text(repo)
    if text is None:
        previous = cached[1] if cached else None
        # Retry sooner than a full TTL when GitHub or the file is unavailable.
        _cache[repo] = (now - CACHE_TTL_SECONDS + 300, previous)
        return previous
    parsed = parse_roadmap(text)
    _cache[repo] = (now, parsed)
    return parsed


def get_all() -> list[dict[str, Any]]:
    """Returns {"project", "roadmap"} for every project with a GitHub repo."""
    projects = [p for p in PROJECTS if "repo" in p]
    with ThreadPoolExecutor(max_workers=8) as pool:
        roadmaps = list(pool.map(lambda p: get_roadmap(p["repo"]), projects))
    return [{"project": p, "roadmap": r} for p, r in zip(projects, roadmaps)]


def clear_cache() -> None:
    """Empties the cache (used by tests)."""
    _cache.clear()
