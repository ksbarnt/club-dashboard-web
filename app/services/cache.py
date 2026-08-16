"""Small hand-rolled TTL cache shared across service modules.

Not for per-user/session state -- only immutable-ish VEX facts (program ids,
a team-number -> id mapping, event cities, the public world-skills table)
that are safe to lose on restart and never keyed by anything secret.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

_lock = threading.Lock()
_store: dict[Any, tuple[Any, float]] = {}


def get_or_set(key: Any, ttl_seconds: float, factory: Callable[[], Any]) -> Any:
    """Return the cached value for ``key``, computing and storing it via
    ``factory`` if missing or expired."""
    now = time.monotonic()
    with _lock:
        cached = _store.get(key)
        if cached is not None and cached[1] > now:
            return cached[0]
    value = factory()
    with _lock:
        _store[key] = (value, now + ttl_seconds)
    return value


def invalidate(key: Optional[Any] = None) -> None:
    """Drop one cache entry, or clear everything if ``key`` is omitted."""
    with _lock:
        if key is None:
            _store.clear()
        else:
            _store.pop(key, None)
