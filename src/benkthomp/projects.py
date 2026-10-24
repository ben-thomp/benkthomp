"""Project data shown on the site. Add an entry here to list a new project."""

GITHUB_USER = "ben-thomp"
GITHUB_URL = f"https://github.com/{GITHUB_USER}"

PROJECTS = [
    {
        "name": "python-clipboard",
        "description": "Clipboard manager inspired by CLCL.",
        "language": "Python",
    },
    {
        "name": "python-date-calc",
        "description": "A date calculation library.",
        "language": "Python",
    },
    {
        "name": "python-excel-csv",
        "description": "A library for Excel and CSV file operations.",
        "language": "Python",
    },
    {
        "name": "python-notes",
        "description": "A small notes app.",
        "language": "Python",
    },
    {
        "name": "python-sdlc",
        "description": "A toolkit for the software development life cycle.",
        "language": "Python",
    },
    {
        "name": "benkthomp",
        "description": "This website. Flask, deployed on Render.",
        "language": "Python",
    },
]


def project_url(project):
    """Return the GitHub URL for a project."""
    return f"{GITHUB_URL}/{project['name']}"
