"""Cached lookup of a package's latest PyPI version and release date.

Uses PyPI's public JSON API. Results share the GitHub reader's cache: cached for
an hour, with the last good copy served if PyPI is unreachable.
"""

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from benkthomp.github import FETCH_TIMEOUT_SECONDS, cached

_URL = "https://pypi.org/pypi/{name}/json"


def _fetch(name: str) -> dict[str, str] | None:
    """Returns {"version", "released"} for a package's latest release, or None."""
    request = urllib.request.Request(
        _URL.format(name=name), headers={"User-Agent": "benkthomp-site"}
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as resp:
            data = json.load(resp)
        files = data.get("urls") or []
        return {
            "version": data["info"]["version"],
            "released": files[0]["upload_time_iso_8601"][:10] if files else "",
        }
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return None


def get_package(name: str) -> dict[str, str] | None:
    """Returns the cached latest {"version", "released"} for a package, or None."""
    return cached("pypi", name, "", lambda: _fetch(name))


def get_packages(names: list[str]) -> dict[str, dict[str, Any] | None]:
    """Looks up several packages at once so a cold cache costs one round trip."""
    if not names:
        return {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(names, pool.map(get_package, names)))
