import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.cache as cache


def _cleanup():
    cache.clear_all()


def test_set_and_get():
    _cleanup()
    cache.set("test_tool", {"value": 42}, ticker="AAA")
    result = cache.get("test_tool", ticker="AAA")
    assert result == {"value": 42}
    _cleanup()


def test_cache_miss_returns_none():
    _cleanup()
    result = cache.get("test_tool", ticker="MISSING")
    assert result is None


def test_ttl_expiry():
    _cleanup()
    cache.set("test_tool", "fresh", ticker="TTL")
    result = cache.get("test_tool", ttl=1, ticker="TTL")
    assert result == "fresh"

    time.sleep(2)
    result = cache.get("test_tool", ttl=1, ticker="TTL")
    assert result is None
    _cleanup()


def test_different_keys_dont_collide():
    _cleanup()
    cache.set("tool_a", "value_a", ticker="X")
    cache.set("tool_b", "value_b", ticker="X")
    assert cache.get("tool_a", ticker="X") == "value_a"
    assert cache.get("tool_b", ticker="X") == "value_b"
    _cleanup()


def test_invalidate():
    _cleanup()
    cache.set("inv_tool", "data", ticker="Y")
    cache.invalidate("inv_tool", ticker="Y")
    assert cache.get("inv_tool", ticker="Y") is None
    _cleanup()


def test_clear_all_returns_count():
    _cleanup()
    cache.set("t1", 1, ticker="A")
    cache.set("t2", 2, ticker="B")
    count = cache.clear_all()
    assert count == 2
