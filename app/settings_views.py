"""The password-gated Settings page. Plain server-rendered form -- no JSON
endpoint reads or writes the settings/teams tables anywhere but here."""

from __future__ import annotations

from typing import List

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from pyvexevents import VexEventsError

from . import db
from .api.active_teams import refresh as refresh_active_teams
from .api.awards import refresh as refresh_awards
from .api.schedule import refresh as refresh_schedule
from .api.world_skills import refresh as refresh_world_skills
from .auth import login_required

settings_bp = Blueprint("settings", __name__)

_REFRESH_FNS = (
    ("active_teams", refresh_active_teams),
    ("world_skills", refresh_world_skills),
    ("awards", refresh_awards),
    ("schedule", refresh_schedule),
)


def _parse_teams() -> List[dict]:
    numbers = request.form.getlist("team_number")
    programs = request.form.getlist("team_program")
    grades = request.form.getlist("team_grade")

    teams = []
    for number, program, grade in zip(numbers, programs, grades):
        number = number.strip()
        if number and program and grade:
            teams.append({"number": number, "program": program, "grade": grade})
    return teams


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    if request.method == "POST":
        api_token = request.form.get("api_token", "").strip()
        event_region = request.form.get("event_region", "").strip()
        viqrc_season = request.form.get("viqrc_season") or None
        v5rc_season = request.form.get("v5rc_season") or None

        db.save_settings(
            api_token=api_token,
            event_region=event_region,
            viqrc_season=int(viqrc_season) if viqrc_season else None,
            v5rc_season=int(v5rc_season) if v5rc_season else None,
            teams=_parse_teams(),
        )
        return redirect(url_for("settings.settings_page", saved=1))

    current = db.get_settings()
    return render_template("settings.html", settings=current, saved=request.args.get("saved") == "1")


@settings_bp.route("/settings/refresh", methods=["POST"])
@login_required
def refresh_now():
    """Run all three cache refreshes synchronously and report per-section
    status, so the Settings page can offer an on-demand "Refresh Now"."""
    results = {}
    for name, fn in _REFRESH_FNS:
        try:
            payload = fn()
        except VexEventsError as exc:
            results[name] = {"status": "error", "message": exc.message}
            continue
        if payload is None:
            results[name] = {"status": "skipped", "message": "Not configured"}
            continue
        cached = db.get_cache(name)
        results[name] = {"status": "ok", "updatedAt": cached["updatedAt"]}
    return jsonify(results)
