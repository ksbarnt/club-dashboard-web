"""Maps pyvexevents/local errors to JSON error responses."""

from __future__ import annotations

from flask import Flask, jsonify
from pyvexevents import (
    VexEventsAuthError,
    VexEventsConnectionError,
    VexEventsError,
    VexEventsHTTPError,
)


class MissingTokenError(Exception):
    """Raised when a request needs a token but none was supplied."""


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(MissingTokenError)
    def _missing_token(exc: MissingTokenError):
        return jsonify({"error": "missing_token", "message": str(exc) or "API token required"}), 400

    @app.errorhandler(VexEventsAuthError)
    def _auth_error(exc: VexEventsAuthError):
        return jsonify({"error": "auth_error", "message": exc.message}), 401

    @app.errorhandler(VexEventsConnectionError)
    def _connection_error(exc: VexEventsConnectionError):
        return jsonify({"error": "connection_error", "message": exc.message}), 502

    @app.errorhandler(VexEventsHTTPError)
    def _http_error(exc: VexEventsHTTPError):
        return jsonify({"error": "vex_http_error", "message": exc.message}), 502

    @app.errorhandler(VexEventsError)
    def _generic_error(exc: VexEventsError):
        return jsonify({"error": "vex_error", "message": exc.message}), 500
