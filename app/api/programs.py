from __future__ import annotations

from flask import jsonify, request

from . import api_bp
from ._common import get_token
from ..auth import login_required
from ..services.resolve import program_id_map
from ..services.vex_client import client_for


@api_bp.route("/seasons")
@login_required
def seasons():
    """VEX season lookup for the Settings page only -- lets it preview
    seasons for a just-typed token before Save. Never touches our own
    settings/teams tables."""
    token = get_token()
    program_abbr = request.args.get("program", "")
    client = client_for(token)

    program_id = program_id_map(client, token).get(program_abbr)
    if program_id is None:
        return jsonify([])

    seasons_list = sorted(
        client.iter_seasons(programs=[program_id]),
        key=lambda s: (s.get("years_start") or 0, s.get("id") or 0),
        reverse=True,
    )
    return jsonify(
        [
            {
                "id": s["id"],
                "name": s.get("name"),
                "years_start": s.get("years_start"),
                "years_end": s.get("years_end"),
            }
            for s in seasons_list
        ]
    )
