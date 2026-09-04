"""The public REST API: read-only access to the cached dashboard data,
authenticated with the static X-API-Key header. Never touches settings/teams."""

from __future__ import annotations

from flask import jsonify

from . import external_bp
from .. import db
from ..auth import require_api_key


def _cached_response(name: str):
    cached = db.get_cache(name)
    if cached is None:
        return (
            jsonify(
                {
                    "error": "not_available",
                    "message": "No cached data yet -- load the dashboard at least once.",
                }
            ),
            404,
        )
    return jsonify({**cached["payload"], "updatedAt": cached["updatedAt"]})


@external_bp.route("/active-teams", methods=["GET"])
@require_api_key
def active_teams():
    return _cached_response("active_teams")


@external_bp.route("/world-skills", methods=["GET"])
@require_api_key
def world_skills():
    return _cached_response("world_skills")


@external_bp.route("/awards", methods=["GET"])
@require_api_key
def awards():
    return _cached_response("awards")


@external_bp.route("/schedule", methods=["GET"])
@require_api_key
def schedule():
    return _cached_response("schedule")
