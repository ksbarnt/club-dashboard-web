from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import jsonify
from pyvexevents import VexEventsNotFoundError

from . import api_bp
from ._common import get_active_settings, require_token
from .. import db
from ..services.concurrency import run_parallel
from ..services.constants import PROGRAM_TABLE_KEY
from ..services.resolve import resolve_team_id
from ..services.vex_client import client_for


def _fetch_detail(client, team_id: int, event_id: int) -> Dict[str, Any]:
    event_rank: Optional[int] = None
    try:
        page = client.get_team_rankings(team_id, events=[event_id])
        rankings = page.get("data") or []
        if rankings:
            event_rank = rankings[0].get("rank")
    except VexEventsNotFoundError:
        pass

    skills_rank: Optional[int] = None
    driver_score = driver_attempts = None
    auto_score = auto_attempts = None
    try:
        page = client.get_team_skills(team_id, events=[event_id])
        for skill in page.get("data") or []:
            if skill.get("rank") is not None:
                skills_rank = skill.get("rank")
            skill_type = skill.get("type")
            if skill_type == "driver":
                driver_score = skill.get("score")
                driver_attempts = skill.get("attempts")
            elif skill_type == "programming":
                auto_score = skill.get("score")
                auto_attempts = skill.get("attempts")
    except VexEventsNotFoundError:
        pass

    return {
        "eventRank": event_rank,
        "skillsRank": skills_rank,
        "driverScore": driver_score,
        "driverAttempts": driver_attempts,
        "autoScore": auto_score,
        "autoAttempts": auto_attempts,
    }


@api_bp.route("/active-teams", methods=["GET"])
def active_teams():
    settings = get_active_settings()
    teams_cfg: List[Dict[str, str]] = settings.get("teams") or []
    if not teams_cfg:
        return jsonify({"IQ": [], "V5": [], "warnings": [], "teamsConfigured": False})

    token = require_token(settings)
    client = client_for(token)

    today = datetime.now().date().isoformat()
    start = f"{today}T00:00:00"
    end = f"{today}T23:59:59"

    def _resolve(team_cfg: Dict[str, str]) -> Tuple[Dict[str, str], Optional[int]]:
        team_id = resolve_team_id(client, token, team_cfg["number"], team_cfg["program"])
        return team_cfg, team_id

    resolved = run_parallel(teams_cfg, _resolve)

    warnings: List[str] = []

    def _events_for(entry: Tuple[Dict[str, str], Optional[int]]) -> List[Dict[str, Any]]:
        _, team_id = entry
        if team_id is None:
            return []
        page = client.get_team_events(team_id, start=start, end=end)
        return page.get("data") or []

    events_lists = run_parallel(resolved, _events_for)

    active_pairs: List[Tuple[Dict[str, str], int, Dict[str, Any]]] = []
    for (team_cfg, team_id), events in zip(resolved, events_lists):
        if team_id is None:
            warnings.append(f"Team {team_cfg['number']} ({team_cfg['program']}): number not found")
            continue
        for event in events:
            active_pairs.append((team_cfg, team_id, event))

    def _detail(pair: Tuple[Dict[str, str], int, Dict[str, Any]]) -> Dict[str, Any]:
        _, team_id, event = pair
        return _fetch_detail(client, team_id, event["id"])

    details = run_parallel(active_pairs, _detail)

    groups: Dict[str, Dict[int, Dict[str, Any]]] = {"IQ": {}, "V5": {}}
    for (team_cfg, _team_id, event), detail in zip(active_pairs, details):
        table_key = PROGRAM_TABLE_KEY.get(team_cfg["program"])
        if table_key is None:
            continue
        event_id = event["id"]
        bucket = groups[table_key].setdefault(
            event_id, {"eventId": event_id, "eventName": event.get("name"), "teams": []}
        )
        bucket["teams"].append({"number": team_cfg["number"], **detail})

    def _finalize(table_key: str) -> List[Dict[str, Any]]:
        event_groups = list(groups[table_key].values())
        event_groups.sort(key=lambda g: g["eventName"] or "")
        for g in event_groups:
            g["teams"].sort(
                key=lambda t: (t["eventRank"] is None, t["eventRank"] if t["eventRank"] is not None else 0)
            )
        return event_groups

    payload = {"IQ": _finalize("IQ"), "V5": _finalize("V5"), "warnings": warnings, "teamsConfigured": True}
    db.save_cache("active_teams", payload)
    return jsonify(payload)
