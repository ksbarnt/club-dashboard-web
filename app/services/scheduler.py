"""Background refresh of the dashboard caches, independent of any
page load. Single-process by design (deployment is systemd running
``python run.py``) -- no leader election/locking needed here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from pyvexevents import VexEventsError


def _run(app: Flask, name: str, fn: Callable[[], Optional[dict]]) -> None:
    with app.app_context():
        try:
            fn()
        except VexEventsError as exc:
            app.logger.warning("%s refresh failed: %s", name, exc.message)
        except Exception:
            app.logger.exception("%s refresh failed unexpectedly", name)


def start(app: Flask) -> None:
    from ..api.active_teams import refresh as refresh_active_teams
    from ..api.awards import refresh as refresh_awards
    from ..api.schedule import refresh as refresh_schedule
    from ..api.world_skills import refresh as refresh_world_skills

    scheduler = BackgroundScheduler(daemon=True)
    now = datetime.now()
    scheduler.add_job(
        lambda: _run(app, "active-teams", refresh_active_teams),
        "interval",
        minutes=5,
        next_run_time=now,
        id="active-teams",
    )
    scheduler.add_job(
        lambda: _run(app, "world-skills", refresh_world_skills),
        "interval",
        days=1,
        next_run_time=now,
        id="world-skills",
    )
    scheduler.add_job(
        lambda: _run(app, "awards", refresh_awards),
        "interval",
        days=1,
        next_run_time=now,
        id="awards",
    )
    scheduler.add_job(
        lambda: _run(app, "schedule", refresh_schedule),
        "interval",
        days=1,
        next_run_time=now,
        id="schedule",
    )
    scheduler.start()
    app.extensions["scheduler"] = scheduler
