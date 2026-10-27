"""Flask application for benkthomp personal website."""

import os
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from benkthomp.projects import PROJECTS, project_url

load_dotenv()


def create_app(config: dict[str, Any] | None = None) -> Flask:
    """Creates and configures a Flask application instance.

    Args:
        config: Optional config overrides applied after env-based defaults.

    Returns:
        A configured Flask application.
    """
    project_root = Path(__file__).parent.parent.parent
    template_folder = project_root / "templates"
    static_folder = project_root / "static"

    app = Flask(
        __name__,
        template_folder=str(template_folder),
        static_folder=str(static_folder),
    )

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
        DEBUG=os.environ.get("FLASK_DEBUG", "true").lower() == "true",
    )

    if config:
        app.config.update(config)

    register_static_versioning(app)
    register_routes(app)

    return app


def register_static_versioning(app: Flask) -> None:
    """Appends ?v=<file mtime> to static URLs so a deploy busts browser caches.

    Args:
        app: The Flask application instance to register the URL default on.
    """

    @app.url_defaults
    def add_static_version(endpoint: str, values: dict[str, Any]) -> None:
        filename = values.get("filename")
        if endpoint != "static" or "v" in values or not filename:
            return
        try:
            values["v"] = int(
                (Path(app.static_folder or "") / filename).stat().st_mtime
            )
        except OSError:
            pass


def register_routes(app: Flask) -> None:
    """Registers all application routes on the given Flask app.

    Args:
        app: The Flask application instance to register routes on.
    """

    @app.route("/")
    def index():
        return render_template("index.html", projects=PROJECTS, project_url=project_url)

    @app.route("/projects")
    def projects():
        return redirect(url_for("index"), code=301)

    def _enclosure_page(subject: str):
        from benkthomp import enclosures

        return render_template(
            "enclosure.html",
            subject=subject,
            info=enclosures.SUBJECTS[subject],
            latest=enclosures.get_latest(subject),
        )

    for _subject in ("gregory", "roxy"):
        app.add_url_rule(
            f"/{_subject}",
            endpoint=_subject,
            view_func=lambda s=_subject: _enclosure_page(s),
        )

    @app.route("/api/enclosures/<subject>/readings")
    def enclosure_readings(subject):
        from benkthomp import enclosures

        if subject not in enclosures.SUBJECTS:
            return jsonify({"error": "unknown subject"}), 404
        hours = min(max(request.args.get("hours", 24, type=int), 1), 24 * 90)
        return jsonify(enclosures.get_readings(subject, hours))

    @app.route("/api/readings", methods=["POST"])
    def ingest_readings():
        from benkthomp import enclosures

        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        if not enclosures.check_ingest_token(token):
            return jsonify({"error": "unauthorized"}), 401
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "bad request"}), 400
        result = enclosures.ingest(payload)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result), 201

    @app.cli.command("seed-enclosures")
    def seed_enclosures():
        """Fill the enclosure DB with synthetic readings (local previews only)."""
        from benkthomp import enclosures

        click.echo(f"Seeded {enclosures.seed_demo()} demo readings.")

    @app.route("/roadmap")
    def roadmap():
        from benkthomp import project_roadmap

        return render_template(
            "roadmap.html",
            entries=project_roadmap.get_all(),
            project_url=project_url,
        )

    @app.route("/projects/<repo>")
    def project(repo):
        from benkthomp import github, project_roadmap
        from benkthomp.projects import find_repo_project

        listed = find_repo_project(repo)
        if listed is None:
            abort(404)
        readme = github.get_text(repo, "README.md")
        return render_template(
            "project.html",
            project=listed,
            github_url=github.repo_url(repo),
            roadmap=project_roadmap.get_roadmap(repo),
            tree=github.get_tree(repo),
            tree_url=lambda path: github.repo_url(repo, path),
            readme_html=github.render_markdown(readme, repo) if readme else None,
        )

    @app.route("/certifications")
    def certifications():
        from benkthomp.roadmap import get_page_data

        return render_template("certifications.html", **get_page_data())

    @app.route("/api/roadmap/auth", methods=["POST"])
    def roadmap_auth():
        from benkthomp.roadmap import check_admin

        key = request.json.get("key", "") if request.is_json else ""
        return jsonify({"ok": check_admin(key)})

    @app.route("/api/roadmap/toggle", methods=["POST"])
    def roadmap_toggle():
        from benkthomp.roadmap import toggle_section

        if not request.is_json:
            return jsonify({"error": "bad request"}), 400
        key = request.headers.get("X-Admin-Key", "")
        result = toggle_section(
            request.json.get("type", ""),
            request.json.get("label", ""),
            key,
        )
        if "error" in result:
            status = 401 if result["error"] == "unauthorized" else 400
            return jsonify(result), status
        return jsonify(result)


if __name__ == "__main__":
    app = create_app()
    print("\nbenkthomp")
    print("Server running at http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
