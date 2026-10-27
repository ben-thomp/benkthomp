"""Project data shown on the home page. Add an entry here to list a new project."""

from flask import url_for

GITHUB_USER = "ben-thomp"
GITHUB_URL = f"https://github.com/{GITHUB_USER}"

# Each project has a `name` and `description`, plus either an `endpoint` (a page
# on this site) or a `repo` (a GitHub repository name). Repos may set `language`.
PROJECTS = [
    {
        "name": "Gregory",
        "description": "Live temperature and humidity for Gregory the boa "
        "constrictor's enclosure.",
        "endpoint": "gregory",
    },
    {
        "name": "Roxy",
        "description": "Live temperature and humidity for Roxy the bearded "
        "dragon's enclosure.",
        "endpoint": "roxy",
    },
    {
        "name": "python-clipboard",
        "description": "Clipboard manager inspired by CLCL.",
        "repo": "python-clipboard",
        "language": "Python",
    },
    {
        "name": "python-date-calc",
        "description": "A date calculation library.",
        "repo": "python-date-calc",
        "language": "Python",
    },
    {
        "name": "python-excel-csv",
        "description": "A library for Excel and CSV file operations.",
        "repo": "python-excel-csv",
        "language": "Python",
    },
    {
        "name": "python-notes",
        "description": "A small notes app.",
        "repo": "python-notes",
        "language": "Python",
    },
    {
        "name": "python-sdlc",
        "description": "A toolkit for the software development life cycle.",
        "repo": "python-sdlc",
        "language": "Python",
    },
    {
        "name": "benkthomp",
        "description": "This website. Flask, deployed on Render.",
        "repo": "benkthomp",
        "language": "Python",
    },
]


def project_url(project: dict[str, str]) -> str:
    """Returns the on-site URL or GitHub URL for a project."""
    if "endpoint" in project:
        return url_for(project["endpoint"])
    return f"{GITHUB_URL}/{project['repo']}"
