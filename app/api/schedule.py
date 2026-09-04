from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flask import current_app, jsonify

from . import api_bp
from ._common import get_active_settings, require_token
from .. import db
from ..services.concurrency import run_parallel
from ..services.constants import team_sort_key
from ..services.errors import MissingTokenError
from ..services.resolve import resolve_team
from ..services.vex_client import client_for


def refresh() -> Optional[Dict[str, Any]]:
    """Fetch fresh full-season Schedule data from VEX and cache it. Returns
    the payload on success, or ``None`` (after logging) if teams/token
    aren't configured yet -- callers treat that as a no-op skip, not an
    error."""
    settings = get_active_settings()
    teams_cfg: List[Dict[str, str]] = settings.get("teams") or []
    if not teams_cfg:
        current_app.logger.info("schedule refresh skipped: no teams configured")
        return None

    try:
        token = require_token(settings)
    except MissingTokenError as exc:
        current_app.logger.info("schedule refresh skipped: %s", exc)
        return None

    client = client_for(token)
    season_ids = {"VIQRC": settings.get("viqrcSeason"), "V5RC": settings.get("v5rcSeason")}

    def _resolve(team_cfg: Dict[str, str]) -> Tuple[Dict[str, str], Optional[dict]]:
        team = resolve_team(client, token, team_cfg["number"], team_cfg["program"])
        return team_cfg, team

    resolved = run_parallel(teams_cfg, _resolve)

    warnings: List[str] = []

    def _events_for(entry: Tuple[Dict[str, str], Optional[dict]]) -> List[Dict[str, Any]]:
        team_cfg, team = entry
        if team is None:
            return []
        season_id = season_ids.get(team_cfg["program"])
        if season_id is None:
            return []
        page = client.get_team_events(team["id"], seasons=[season_id])
        return page.get("data") or []

    events_lists = run_parallel(resolved, _events_for)

    groups: Dict[int, Dict[str, Any]] = {}
    for (team_cfg, team), events in zip(resolved, events_lists):
        if team is None:
            warnings.append(f"Team {team_cfg['number']} ({team_cfg['program']}): number not found")
            continue
        if season_ids.get(team_cfg["program"]) is None:
            continue
        for event in events:
            event_id = event["id"]
            bucket = groups.setdefault(
                event_id,
                {
                    "eventId": event_id,
                    "eventName": event.get("name"),
                    "sku": event.get("sku"),
                    "start": event.get("start"),
                    "end": event.get("end"),
                    "teams": [],
                },
            )
            bucket["teams"].append(
                {"number": team_cfg["number"], "name": team.get("name"), "program": team_cfg["program"]}
            )

    event_groups = list(groups.values())
    event_groups.sort(key=lambda g: g["start"] or "")
    for g in event_groups:
        g["teams"].sort(key=lambda t: team_sort_key(t["number"]))

    payload = {"events": event_groups, "warnings": warnings, "teamsConfigured": True}
    db.save_cache("schedule", payload)
    return payload


@api_bp.route("/schedule", methods=["GET"])
def schedule():
    cached = db.get_cache("schedule")
    if cached is None:
        return jsonify({"events": [], "warnings": [], "teamsConfigured": False})
    return jsonify(cached["payload"])
