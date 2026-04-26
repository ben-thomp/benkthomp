"""Flask application for benkthomp personal website."""

import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request


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

    register_routes(app)

    return app


def register_routes(app: Flask) -> None:
    """Registers all application routes on the given Flask app.

    Args:
        app: The Flask application instance to register routes on.
    """

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/projects")
    def projects():
        return render_template("projects.html")

    @app.route("/roadmap")
    def roadmap():
        from benkthomp.roadmap import get_page_data

        return render_template("roadmap.html", **get_page_data())

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
