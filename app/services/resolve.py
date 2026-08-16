"""Team/program id resolution and event lookups, all cache-backed.

The VEX Events API keys most endpoints off numeric ids (team id, program
id) while our Settings UI only stores human-facing values (team number,
"VIQRC"/"V5RC", grade). These helpers bridge that gap.
"""

from __future__ import annotations

from typing import Optional

from pyvexevents import VexEventsClient, VexEventsNotFoundError

from . import cache

PROGRAM_MAP_TTL = 60 * 60 * 24  # programs essentially never change
TEAM_ID_TTL = 60 * 60
EVENT_TTL = 60 * 60 * 24


def program_id_map(client: VexEventsClient, token: str) -> dict[str, int]:
    """{"VIQRC": id, "V5RC": id, ...} keyed off Program.abbr."""

    def _fetch() -> dict[str, int]:
        mapping: dict[str, int] = {}
        for program in client.iter_programs():
            abbr = program.get("abbr")
            if abbr:
                mapping[abbr] = program["id"]
        return mapping

    return cache.get_or_set(("program_id_map", token), PROGRAM_MAP_TTL, _fetch)


def resolve_team_id(
    client: VexEventsClient, token: str, number: str, program_abbr: str
) -> Optional[int]:
    """Team number + program abbreviation -> numeric team id, or None."""

    def _fetch() -> Optional[int]:
        program_ids = program_id_map(client, token)
        program_id = program_ids.get(program_abbr)
        programs = [program_id] if program_id is not None else None
        page = client.get_teams(numbers=[number], programs=programs)
        for team in page.get("data") or []:
            team_program = team.get("program") or {}
            if program_id is not None and team_program.get("id") == program_id:
                return team["id"]
            if team_program.get("code") == program_abbr:
                return team["id"]
        # No program filter matched (e.g. program_id lookup failed) -- fall
        # back to the first result for this number, if any.
        data = page.get("data") or []
        return data[0]["id"] if data and program_id is None else None

    return cache.get_or_set(("team_id", token, number, program_abbr), TEAM_ID_TTL, _fetch)


def event_details(client: VexEventsClient, token: str, event_id: int) -> Optional[dict]:
    """{"city": ..., "start": ...} for an event, or None if not found."""

    def _fetch() -> Optional[dict]:
        try:
            event = client.get_event(event_id)
        except VexEventsNotFoundError:
            return None
        location = event.get("location") or {}
        return {"city": location.get("city"), "start": event.get("start")}

    return cache.get_or_set(("event_details", token, event_id), EVENT_TTL, _fetch)
