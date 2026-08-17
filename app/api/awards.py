from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app, jsonify

from . import api_bp
from ._common import get_active_settings, require_token
from .. import db
from ..services.concurrency import run_parallel
from ..services.constants import team_sort_key
from ..services.errors import MissingTokenError
from ..services.resolve import event_details, resolve_team_id
from ..services.vex_client import client_for


def _format_event_date(start: Optional[str]) -> Optional[str]:
    """RFC3339 datetime -> "M/D" (no leading zeros, no year)."""
    if not start:
        return None
    value = start[:-1] + "+00:00" if start.endswith("Z") else start
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return f"{dt.month}/{dt.day}"


def _format_event_label(city: Optional[str], start: Optional[str]) -> Optional[str]:
    date_str = _format_event_date(start)
    if city and date_str:
        return f"{city} {date_str}"
    return city or date_str


def refresh() -> Optional[Dict[str, Any]]:
    """Fetch fresh Awards data from VEX and cache it. Returns the payload
    on success, or ``None`` (after logging) if teams/token aren't
    configured yet -- callers treat that as a no-op skip, not an error."""
    settings = get_active_settings()
    teams_cfg: List[Dict[str, str]] = settings.get("teams") or []
    if not teams_cfg:
        current_app.logger.info("awards refresh skipped: no teams configured")
        return None

    try:
        token = require_token(settings)
    except MissingTokenError as exc:
        current_app.logger.info("awards refresh skipped: %s", exc)
        return None

    client = client_for(token)
    season_ids = {"VIQRC": settings.get("viqrcSeason"), "V5RC": settings.get("v5rcSeason")}

    def _resolve(team_cfg: Dict[str, str]) -> Tuple[Dict[str, str], Optional[int]]:
        team_id = resolve_team_id(client, token, team_cfg["number"], team_cfg["program"])
        return team_cfg, team_id

    resolved = run_parallel(teams_cfg, _resolve)

    warnings: List[str] = []

    def _awards_for(entry: Tuple[Dict[str, str], Optional[int]]) -> List[Dict[str, Any]]:
        team_cfg, team_id = entry
        if team_id is None:
            return []
        season_id = season_ids.get(team_cfg["program"])
        if season_id is None:
            return []
        page = client.get_team_awards(team_id, seasons=[season_id])
        return page.get("data") or []

    awards_lists = run_parallel(resolved, _awards_for)

    event_ids = set()
    for (team_cfg, team_id), team_awards in zip(resolved, awards_lists):
        if team_id is None:
            warnings.append(f"Team {team_cfg['number']} ({team_cfg['program']}): number not found")
            continue
        for award in team_awards:
            event_id = (award.get("event") or {}).get("id")
            if event_id is not None:
                event_ids.add(event_id)

    def _details_for(event_id: int) -> Tuple[int, Optional[Dict[str, Any]]]:
        return event_id, event_details(client, token, event_id)

    event_info = {eid: (info or {}) for eid, info in run_parallel(list(event_ids), _details_for)}

    buckets: Dict[str, List[Dict[str, Any]]] = {"VIQRC": [], "V5RC": []}
    for (team_cfg, team_id), team_awards in zip(resolved, awards_lists):
        if team_id is None or not team_awards:
            continue

        by_event: Dict[Optional[int], List[Dict[str, Any]]] = {}
        for award in team_awards:
            event_id = (award.get("event") or {}).get("id")
            by_event.setdefault(event_id, []).append(award)

        events_out = []
        for event_id, award_list in by_event.items():
            award_list.sort(key=lambda a: a.get("order") if a.get("order") is not None else 0)
            info = event_info.get(event_id, {})
            events_out.append(
                {
                    "eventId": event_id,
                    "eventLabel": _format_event_label(info.get("city"), info.get("start")),
                    "_start": info.get("start") or "",
                    "awards": [{"title": a.get("title"), "order": a.get("order")} for a in award_list],
                }
            )
        events_out.sort(key=lambda e: e["_start"])
        for e in events_out:
            e.pop("_start", None)

        bucket = buckets.get(team_cfg["program"])
        if bucket is None:
            continue
        bucket.append({"number": team_cfg["number"], "events": events_out})

    for key in buckets:
        buckets[key].sort(key=lambda t: team_sort_key(t["number"]))

    payload = {"VIQRC": buckets["VIQRC"], "V5RC": buckets["V5RC"], "warnings": warnings, "teamsConfigured": True}
    db.save_cache("awards", payload)
    return payload


@api_bp.route("/awards", methods=["GET"])
def awards():
    cached = db.get_cache("awards")
    if cached is None:
        return jsonify({"VIQRC": [], "V5RC": [], "warnings": [], "teamsConfigured": False})
    return jsonify(cached["payload"])
