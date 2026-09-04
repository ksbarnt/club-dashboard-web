from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")
external_bp = Blueprint("api_external", __name__, url_prefix="/api/external")

from . import active_teams, awards, programs, schedule, world_skills, external  # noqa: E402,F401
