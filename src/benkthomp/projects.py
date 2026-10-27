"""Project data shown on the home page. Add an entry here to list a new project."""

from flask import url_for

GITHUB_USER = "ben-thomp"
GITHUB_URL = f"https://github.com/{GITHUB_USER}"

# Each project has a `name`, `description` and home page `section`, plus either an
# `endpoint` (a page on this site) or a `repo` (a GitHub repository name, shown on
# /projects/<repo>). A `pypi` package name adds its latest version to the home page.
PROJECTS = [
    {
        "name": "Gregory",
        "description": "Live temperature and humidity for Gregory the boa "
        "constrictor's enclosure.",
        "endpoint": "gregory",
        "section": "enclosures",
    },
    {
        "name": "Roxy",
        "description": "Live temperature and humidity for Roxy the bearded "
        "dragon's enclosure.",
        "endpoint": "roxy",
        "section": "enclosures",
    },
    {
        "name": "python-clipboard",
        "description": "Clipboard manager inspired by CLCL.",
        "repo": "python-clipboard",
        "pypi": "python-clipboard",
        "section": "packages",
        "language": "Python",
    },
    {
        "name": "python-date-calc",
        "description": "A date calculation library.",
        "repo": "python-date-calc",
        "pypi": "python-date-calc",
        "section": "packages",
        "language": "Python",
    },
    {
        "name": "python-excel-csv",
        "description": "A library for Excel and CSV file operations.",
        "repo": "python-excel-csv",
        "pypi": "python-excel-csv",
        "section": "packages",
        "language": "Python",
    },
    {
        "name": "python-notes",
        "description": "A small notes app.",
        "repo": "python-notes",
        "pypi": "python-notes",
        "section": "packages",
        "language": "Python",
    },
    {
        "name": "python-sdlc",
        "description": "A toolkit for the software development life cycle.",
        "repo": "python-sdlc",
        "pypi": "python-sdlc",
        "section": "packages",
        "language": "Python",
    },
    {
        "name": "benkthomp",
        "description": "This website. Flask, deployed on Render.",
        "repo": "benkthomp",
        "section": "site",
        "language": "Python",
    },
    {
        "name": "Roadmap",
        "description": "What each project is working on and what comes next.",
        "endpoint": "roadmap",
        "section": "site",
    },
]

# Home page groups, in display order: (section key, heading).
SECTIONS = [
    ("enclosures", "Enclosures"),
    ("packages", "Packages"),
    ("site", "Site"),
]


def project_url(project: dict[str, str]) -> str:
    """Returns the on-site URL for a project (its own page or its repo page)."""
    if "endpoint" in project:
        return url_for(project["endpoint"])
    return url_for("project", repo=project["repo"])


def find_repo_project(repo: str) -> dict[str, str] | None:
    """Returns the listed project for a repo name, or None."""
    return next((p for p in PROJECTS if p.get("repo") == repo), None)


def grouped_projects() -> list[tuple[str, list[dict[str, str]]]]:
    """Returns [(heading, projects)] for each home page section, in order."""
    return [
        (heading, [p for p in PROJECTS if p.get("section") == key])
        for key, heading in SECTIONS
    ]
