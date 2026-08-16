from __future__ import annotations

from typing import Any, Dict, List, Tuple

from flask import jsonify

from . import api_bp
from ._common import get_active_settings
from .. import db
from ..services.cache import get_or_set
from ..services.constants import GRADE_TO_SKILLS_LEVEL, world_skills_group_sort_key
from ..services.vex_client import client_for

WORLD_SKILLS_TTL = 60 * 10  # public/unauthenticated endpoint, same for everyone


def _world_skills_rankings(client, season_id: int, grade_level: str) -> List[Dict[str, Any]]:
    def _fetch() -> List[Dict[str, Any]]:
        return client.get_world_skills_rankings(season_id, grade_level)

    return get_or_set(("world_skills", season_id, grade_level), WORLD_SKILLS_TTL, _fetch)


@api_bp.route("/world-skills", methods=["GET"])
def world_skills():
    settings = get_active_settings()
    teams_cfg: List[Dict[str, str]] = settings.get("teams") or []
    event_region: str = settings.get("eventRegion") or ""

    if not teams_cfg or not event_region:
        return jsonify(
            {
                "groups": [],
                "eventRegion": event_region,
                "teamsConfigured": bool(teams_cfg),
                "eventRegionConfigured": bool(event_region),
            }
        )

    season_ids = {"VIQRC": settings.get("viqrcSeason"), "V5RC": settings.get("v5rcSeason")}

    # This endpoint is public/unauthenticated -- no token needed.
    client = client_for(None)

    combos: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for team_cfg in teams_cfg:
        key = (team_cfg["program"], team_cfg["grade"])
        combos.setdefault(key, []).append(team_cfg)

    groups: List[Dict[str, Any]] = []
    for (program, grade), members in combos.items():
        season_id = season_ids.get(program)
        grade_level = GRADE_TO_SKILLS_LEVEL.get(grade)
        if season_id is None or grade_level is None:
            continue

        world_list = _world_skills_rankings(client, season_id, grade_level)

        by_number: Dict[str, Dict[str, Any]] = {}
        for entry in world_list:
            number = (entry.get("team") or {}).get("team")
            if number:
                by_number[number] = entry

        region_rank_by_number: Dict[str, int] = {}
        if event_region:
            idx = 0
            for entry in world_list:
                team_info = entry.get("team") or {}
                if team_info.get("eventRegion") == event_region:
                    idx += 1
                    number = team_info.get("team")
                    if number:
                        region_rank_by_number[number] = idx

        rows: List[Dict[str, Any]] = []
        for team_cfg in members:
            entry = by_number.get(team_cfg["number"])
            if entry is None:
                # No world skills record for this team -- omit (per spec).
                continue
            scores = entry.get("scores") or {}
            rows.append(
                {
                    "number": team_cfg["number"],
                    "regionalRank": region_rank_by_number.get(team_cfg["number"]),
                    "worldRank": entry.get("rank"),
                    "overallScore": scores.get("score"),
                    "driverScore": scores.get("driver"),
                    "autoScore": scores.get("programming"),
                }
            )

        if rows:
            rows.sort(key=lambda r: (r["regionalRank"] is None, r["regionalRank"] or 0))
            groups.append({"program": program, "grade": grade, "teams": rows})

    groups.sort(key=lambda g: world_skills_group_sort_key(g["program"], g["grade"]))

    payload = {
        "groups": groups,
        "eventRegion": event_region,
        "teamsConfigured": True,
        "eventRegionConfigured": True,
    }
    db.save_cache("world_skills", payload)
    return jsonify(payload)
