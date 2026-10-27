"""Cached read-only access to public GitHub repos: files, file trees, READMEs.

Text files come from raw.githubusercontent.com, trees from the GitHub API
(set GITHUB_TOKEN to raise its rate limit). Results are cached for an hour and
the last good copy is served if GitHub is unreachable.

For local development, set PROJECTS_LOCAL_DIR to a folder of sibling repos and
files and trees are read from disk instead.
"""

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote

from markdown_it import MarkdownIt

from benkthomp.projects import GITHUB_USER

CACHE_TTL_SECONDS = 3600
RETRY_AFTER_FAILURE_SECONDS = 300
FETCH_TIMEOUT_SECONDS = 5
MAX_TREE_ENTRIES = 500

_RAW_URL = "https://raw.githubusercontent.com/{user}/{repo}/HEAD/{path}"
_TREE_URL = "https://api.github.com/repos/{user}/{repo}/git/trees/HEAD?recursive=1"

# key -> (fetched_at, value or None)
_cache: dict[tuple[str, str, str], tuple[float, Any]] = {}


def repo_url(repo: str, path: str = "") -> str:
    """Returns the GitHub URL for a repo, or for a path inside it."""
    base = f"https://github.com/{GITHUB_USER}/{repo}"
    return f"{base}/blob/HEAD/{quote(path)}" if path else base


def _local_dir() -> Path | None:
    value = os.environ.get("PROJECTS_LOCAL_DIR")
    return Path(value) if value else None


def _open(url: str) -> bytes | None:
    headers = {"User-Agent": "benkthomp-site"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError):
        return None


def _fetch_text(repo: str, path: str) -> str | None:
    """Returns a file's text from a repo, or None if unavailable."""
    local = _local_dir()
    if local:
        file = local / repo / path
        return file.read_text(encoding="utf-8") if file.is_file() else None
    data = _open(_RAW_URL.format(user=GITHUB_USER, repo=repo, path=quote(path)))
    try:
        return data.decode("utf-8") if data is not None else None
    except UnicodeDecodeError:
        return None


def _fetch_tree(repo: str) -> list[dict[str, str]] | None:
    """Returns [{"path", "type"}] for every file and folder, or None."""
    local = _local_dir()
    if local:
        try:
            out = subprocess.run(
                ["git", "-C", str(local / repo), "ls-files"],
                capture_output=True,
                text=True,
                timeout=FETCH_TIMEOUT_SECONDS,
                check=True,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        entries = {}
        for line in out.splitlines():
            parts = line.split("/")
            for i in range(1, len(parts)):
                entries["/".join(parts[:i])] = "tree"
            entries[line] = "blob"
        return [{"path": p, "type": t} for p, t in entries.items()]
    data = _open(_TREE_URL.format(user=GITHUB_USER, repo=repo))
    if data is None:
        return None
    try:
        tree = json.loads(data)["tree"]
    except (ValueError, KeyError, TypeError):
        return None
    return [{"path": e["path"], "type": e["type"]} for e in tree]


def cached(kind: str, repo: str, path: str, fetch: Any) -> Any:
    """Returns fetch()'s value, cached; on failure keeps the previous value."""
    key = (kind, repo, path)
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    value = fetch()
    if value is None:
        previous = hit[1] if hit else None
        # Retry sooner than a full TTL when GitHub or the file is unavailable.
        _cache[key] = (now - CACHE_TTL_SECONDS + RETRY_AFTER_FAILURE_SECONDS, previous)
        return previous
    _cache[key] = (now, value)
    return value


def get_text(repo: str, path: str) -> str | None:
    """Returns a cached text file from a repo, or None if never available."""
    return cached("text", repo, path, lambda: _fetch_text(repo, path))


def get_tree(repo: str) -> list[dict[str, Any]] | None:
    """Returns the repo's file tree as nested nodes (folders first), or None.

    Each node is {"name", "path", "is_dir", "children"}. Trees over
    MAX_TREE_ENTRIES entries are cut off and flagged by a final "truncated" node.
    """
    entries = cached("tree", repo, "", lambda: _fetch_tree(repo))
    return None if entries is None else build_tree(entries)


def build_tree(entries: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Nests flat {"path", "type"} entries into a sorted folder tree."""
    root: dict[str, Any] = {"children": {}}
    for entry in sorted(entries, key=lambda e: e["path"])[:MAX_TREE_ENTRIES]:
        node = root
        parts = entry["path"].split("/")
        for i, part in enumerate(parts):
            is_last = i == len(parts) - 1
            children = node["children"]
            if part not in children:
                children[part] = {
                    "name": part,
                    "path": "/".join(parts[: i + 1]),
                    "is_dir": not is_last or entry["type"] == "tree",
                    "children": {},
                }
            node = children[part]

    def finish(node: dict[str, Any]) -> list[dict[str, Any]]:
        kids = [{**c, "children": finish(c)} for c in node["children"].values()]
        return sorted(kids, key=lambda c: (not c["is_dir"], c["name"].lower()))

    result = finish(root)
    if len(entries) > MAX_TREE_ENTRIES:
        result.append(
            {
                "name": "…",
                "path": "",
                "is_dir": False,
                "children": [],
                "truncated": True,
            }
        )
    return result


_ABSOLUTE = re.compile(r"^([a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)


def render_markdown(text: str, repo: str) -> str:
    """Renders README markdown to safe HTML (raw HTML is escaped).

    Relative links and images are pointed at the repo on GitHub.
    """
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = md.parse(text)

    def fix(token: Any) -> None:
        for child in token.children or []:
            fix(child)
        attr = {"link_open": "href", "image": "src"}.get(token.type)
        value = token.attrGet(attr) if attr else None
        if isinstance(value, str) and value and not _ABSOLUTE.match(value):
            relative = value[2:] if value.startswith("./") else value.lstrip("/")
            if attr == "src":
                base = f"https://raw.githubusercontent.com/{GITHUB_USER}/{repo}/HEAD/"
                token.attrSet("src", base + quote(relative))
            else:
                token.attrSet("href", repo_url(repo, relative))

    for token in tokens:
        fix(token)
    return md.renderer.render(tokens, md.options, {})


def clear_cache() -> None:
    """Empties the cache (used by tests)."""
    _cache.clear()
