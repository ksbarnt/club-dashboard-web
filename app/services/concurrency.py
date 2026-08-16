"""Bounded fan-out helper for per-team API calls."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, List, TypeVar

T = TypeVar("T")
R = TypeVar("R")

MAX_WORKERS = 8


def run_parallel(items: Iterable[T], fn: Callable[[T], R]) -> List[R]:
    """Apply ``fn`` to every item using a small thread pool, preserving order."""
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(items))) as pool:
        return list(pool.map(fn, items))
