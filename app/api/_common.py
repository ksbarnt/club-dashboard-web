from __future__ import annotations

from typing import Any, Dict

from flask import request

from .. import db
from ..services.errors import MissingTokenError


def get_token() -> str:
    """Header-supplied VEX token, used only by the /api/seasons helper the
    (already logged-in) settings page calls to preview seasons for a
    token before it's saved."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[len("Bearer ") :].strip()
        if token:
            return token
    raise MissingTokenError("Missing or invalid Authorization header")


def get_active_settings() -> Dict[str, Any]:
    """The server's own view of Settings, for the public dashboard-fetch
    endpoints. Never returned to a client -- only its derived, computed
    results are."""
    return db.get_settings()


def require_token(settings: Dict[str, Any]) -> str:
    token = settings.get("apiToken") or ""
    if not token:
        raise MissingTokenError("No VEX Events API token configured in Settings")
    return token
