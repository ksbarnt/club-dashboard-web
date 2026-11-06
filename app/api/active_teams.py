from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app, jsonify
from pyvexevents import VexEventsNotFoundError

from . import api_bp
from ._common import get_active_settings, require_token
from .. import db
from ..services.concurrency import run_parallel
from ..services.constants import PROGRAM_TABLE_KEY
from ..services.errors import MissingTokenError
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


# How far back to look for events that may still be running today. Leagues
# are a single event spanning months, so a start-of-today filter misses them.
_LOOKBACK_DAYS = 365


def _is_active_on(event: Dict[str, Any], day: date) -> bool:
    """True if ``event`` is running on ``day``.

    Leagues list each session date as a key in ``locations``; when there's
    more than one, only those session days count. Otherwise (single- or
    multi-day tournaments, which list just their first day) any day within
    start..end counts."""
    iso = day.isoformat()
    session_days = [k for k in (event.get("locations") or {}) if len(k) == 10 and k[4] == "-"]
    if len(session_days) > 1:
        return iso in session_days
    start = (event.get("start") or "")[:10]
    end = (event.get("end") or "")[:10] or start
    return bool(start) and start <= iso <= end


def refresh() -> Optional[Dict[str, Any]]:
    """Fetch fresh Active Teams data from VEX and cache it. Returns the
    payload on success, or ``None`` (after logging) if teams/token aren't
    configured yet -- callers treat that as a no-op skip, not an error."""
    settings = get_active_settings()
    teams_cfg: List[Dict[str, str]] = settings.get("teams") or []
    if not teams_cfg:
        current_app.logger.info("active-teams refresh skipped: no teams configured")
        return None

    try:
        token = require_token(settings)
    except MissingTokenError as exc:
        current_app.logger.info("active-teams refresh skipped: %s", exc)
        return None

    client = client_for(token)

    today = datetime.now().date()
    # The API's start/end filters mean "starts on/after" and "ends on/before",
    # so filtering by today drops leagues and multi-day events. Fetch a wide
    # window by start date and decide what's running today locally.
    window_start = f"{(today - timedelta(days=_LOOKBACK_DAYS)).isoformat()}T00:00:00"

    def _resolve(team_cfg: Dict[str, str]) -> Tuple[Dict[str, str], Optional[int]]:
        team_id = resolve_team_id(client, token, team_cfg["number"], team_cfg["program"])
        return team_cfg, team_id

    resolved = run_parallel(teams_cfg, _resolve)

    warnings: List[str] = []

    def _events_for(entry: Tuple[Dict[str, str], Optional[int]]) -> List[Dict[str, Any]]:
        _, team_id = entry
        if team_id is None:
            return []
        page = client.get_team_events(team_id, start=window_start, per_page=250)
        return [e for e in page.get("data") or [] if _is_active_on(e, today)]

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
    return payload


@api_bp.route("/active-teams", methods=["GET"])
def active_teams():
    cached = db.get_cache("active_teams")
    if cached is None:
        return jsonify({"IQ": [], "V5": [], "warnings": [], "teamsConfigured": False})
    return jsonify(cached["payload"])
