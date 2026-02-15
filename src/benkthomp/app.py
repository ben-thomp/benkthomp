"""Flask application for benkthomp personal website."""

import os
from pathlib import Path

from flask import Flask, render_template


def create_app(config=None):
    """Application factory for creating Flask app instances."""
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


def register_routes(app):
    """Register all application routes."""

    @app.route("/")
    def index():
        """Render the home page."""
        return render_template("index.html")

    @app.route("/about")
    def about():
        """Render the about page."""
        return render_template("about.html")

    @app.route("/projects")
    def projects():
        """Render the projects page."""
        return render_template("projects.html")

    @app.route("/contact")
    def contact():
        """Render the contact page."""
        return render_template("contact.html")


if __name__ == "__main__":
    app = create_app()
    print("\nbenkthomp")
    print("Server running at http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
