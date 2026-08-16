"""Settings-page session login and the static-key decorator for the
external cached-data API. Two unrelated auth mechanisms, kept in one
module because both compare a SHA-256 hash pulled from .env."""

from __future__ import annotations

import hashlib
import hmac
import os
from functools import wraps
from typing import Callable

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _matches_hash(value: str, env_var: str) -> bool:
    expected = os.environ.get(env_var, "")
    if not expected or not value:
        return False
    return hmac.compare_digest(_sha256(value), expected.strip().lower())


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def require_api_key(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        key = request.headers.get("X-API-Key", "")
        if not _matches_hash(key, "API_KEY_SHA256"):
            return jsonify({"error": "unauthorized", "message": "Missing or invalid X-API-Key header"}), 401
        return view(*args, **kwargs)

    return wrapped


@auth_bp.route("/settings/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if _matches_hash(password, "SETTINGS_PASSWORD_SHA256"):
            session.clear()
            session["authenticated"] = True
            session.permanent = True
            next_url = request.args.get("next") or url_for("settings.settings_page")
            return redirect(next_url)
        error = "Incorrect password."
    return render_template("login.html", error=error)


@auth_bp.route("/settings/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
