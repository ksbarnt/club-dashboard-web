"""Shared HTTP plumbing for talking to events.vex.com via pyvexevents."""

from __future__ import annotations

from typing import Optional

import requests
from pyvexevents import VexEventsClient

# Reused across every request for connection pooling. Never closed until
# process exit, which is fine for a long-lived desktop app.
_SHARED_SESSION = requests.Session()


def client_for(token: Optional[str]) -> VexEventsClient:
    """Build a client that borrows (does not own/close) the shared session.

    ``token`` may be ``None`` for the world-skills endpoint, the only
    unauthenticated call in the API.
    """
    return VexEventsClient(token=token, session=_SHARED_SESSION)
