from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

REQUIRED_ENV_VARS = ["FLASK_SECRET_KEY", "SETTINGS_PASSWORD_SHA256", "API_KEY_SHA256"]


def create_app() -> Flask:
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing required .env vars: {', '.join(missing)}. "
            "Copy .env.example to .env and fill them in."
        )

    from . import db
    from .api import api_bp, external_bp
    from .auth import auth_bp
    from .services.errors import register_error_handlers
    from .settings_views import settings_bp

    app = Flask(
        __name__,
        static_folder=str(PROJECT_ROOT / "static"),
        template_folder=str(PROJECT_ROOT / "templates"),
    )

    app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() != "false"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.permanent_session_lifetime = timedelta(hours=12)

    db.init_app(app)

    app.register_blueprint(api_bp)
    app.register_blueprint(external_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(settings_bp)
    register_error_handlers(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
