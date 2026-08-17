# club-dashboard-web

VEX Robotics team dashboard (Active Teams, World Skills, Awards) for a public web server. Based on [club-dashboard-desktop](../club-dashboard-desktop), with three changes:

- Settings (VEX API token, event region, seasons, tracked teams) live in a server-side **SQLite** database (`instance/club_dashboard.db`) instead of browser localStorage.
- The Settings page is **not linked** from the main dashboard nav and is **password-protected** (`/settings`, gated by a login at `/settings/login`).
- The last data shown on each dashboard view is cached in SQLite and exposed read-only via a **static-key REST API** at `/api/external/*` for external consumers. This API never has any access to Settings.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"                          # FLASK_SECRET_KEY
python3 -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"    # SETTINGS_PASSWORD_SHA256
python3 -c "import hashlib; print(hashlib.sha256(b'yourapikey').hexdigest())"      # API_KEY_SHA256
```

The `.env` file stores only the SHA-256 **hashes** of the password and API key, never the plaintext values. Keep the plaintext password/key somewhere safe (e.g. a password manager) — they can't be recovered from the hash.

## Run (development)

```bash
python run.py
```

Serves on `http://0.0.0.0:5000`. For local HTTP-only testing, set `SESSION_COOKIE_SECURE=false` in `.env` — the settings-page login sets a `Secure` cookie by default, which browsers won't send back over plain HTTP.

## Run (production)

Deployment is a single `python run.py` process managed by systemd, behind a reverse proxy (nginx, Caddy) that terminates TLS. Leave `SESSION_COOKIE_SECURE=true` (the default) in production — it requires HTTPS in front of the app.

The background refresh scheduler (see below) assumes a single process — don't run more than one instance against the same `instance/` dir at a time, or the same VEX API calls will fire redundantly from each.

Alternatively, `gunicorn -w 2 -b 0.0.0.0:8000 wsgi:application` still works as a WSGI server, but note the scheduler isn't multi-worker-safe: with more than one worker, each worker runs its own copy of the schedule.

## Using the dashboard

1. Visit `/settings/login`, sign in with the password you hashed above, and configure the VEX API token, event region, seasons, and tracked teams at `/settings`.
2. A background scheduler refreshes each dataset from the VEX Events API automatically, independent of anyone loading a page: Active Teams every 5 minutes, World Skills and Awards once a day. Each also refreshes once immediately on startup. The Settings page has a **Refresh Now** button to trigger all three on demand and see when each last updated.
3. The public dashboard at `/` (Active Teams, World Skills, Awards) just reads that cached data — no login needed to view it, and no live VEX API call happens on page load.
4. The same cached data is readable externally:

   ```bash
   curl -H "X-API-Key: yourapikey" http://localhost:8000/api/external/active-teams
   curl -H "X-API-Key: yourapikey" http://localhost:8000/api/external/world-skills
   curl -H "X-API-Key: yourapikey" http://localhost:8000/api/external/awards
   ```

   Returns 404 until the corresponding dataset has been refreshed at least once (e.g. Settings isn't configured yet), and 401 for a missing/incorrect key.
