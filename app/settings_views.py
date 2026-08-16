"""The password-gated Settings page. Plain server-rendered form -- no JSON
endpoint reads or writes the settings/teams tables anywhere but here."""

from __future__ import annotations

from typing import List

from flask import Blueprint, redirect, render_template, request, url_for

from . import db
from .auth import login_required

settings_bp = Blueprint("settings", __name__)


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
