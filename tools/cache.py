"""Disk-based JSON cache with TTL. Avoids re-fetching the same ticker data within a session."""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

# Allow override via environment variable so CI and tests can redirect the cache
CACHE_DIR = Path(os.environ.get("CACHE_DIR", ".cache"))
DEFAULT_TTL = 3600  # 1 hour

logger = logging.getLogger(__name__)


def _key(tool: str, **kwargs) -> str:
    payload = json.dumps({"tool": tool, **kwargs}, sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()


def get(tool: str, ttl: int = DEFAULT_TTL, **kwargs) -> Any | None:
    path = CACHE_DIR / f"{_key(tool, **kwargs)}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data["ts"] > ttl:
            path.unlink(missing_ok=True)
            return None
        logger.debug(f"Cache hit: {tool}({kwargs})")
        return data["v"]
    except Exception:
        return None


def set(tool: str, value: Any, **kwargs) -> None:  # noqa: A001
    """Write a cache entry atomically: write to .tmp then rename.

    Atomic rename prevents a partially-written file from being read as valid
    cache data if the process is interrupted mid-write.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{_key(tool, **kwargs)}.json"
    tmp_path = path.with_suffix(".json.tmp")
    try:
        tmp_path.write_text(json.dumps({"ts": time.time(), "v": value}))
        tmp_path.rename(path)
    except Exception as exc:
        logger.warning(f"Cache write failed: {exc}")
        tmp_path.unlink(missing_ok=True)


def invalidate(tool: str, **kwargs) -> None:
    path = CACHE_DIR / f"{_key(tool, **kwargs)}.json"
    path.unlink(missing_ok=True)


def clear_all() -> int:
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
        count += 1
    return count


def stats() -> dict:
    """Return the number of cached entries and their total size in bytes."""
    if not CACHE_DIR.exists():
        return {"count": 0, "total_bytes": 0}
    files = list(CACHE_DIR.glob("*.json"))
    total_bytes = sum(f.stat().st_size for f in files)
    return {"count": len(files), "total_bytes": total_bytes}
