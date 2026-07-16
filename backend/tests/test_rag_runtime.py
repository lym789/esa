from concurrent.futures import ThreadPoolExecutor
from time import sleep

from app.services.rag_runtime import BoundedTTLCache


def test_bounded_ttl_cache_evicts_lru_and_expires_entries():
    cache = BoundedTTLCache()
    cache.set("first", {"value": 1}, ttl_seconds=1, max_entries=2)
    cache.set("second", {"value": 2}, ttl_seconds=1, max_entries=2)
    assert cache.get("first") == {"value": 1}
    cache.set("third", {"value": 3}, ttl_seconds=1, max_entries=2)

    assert cache.get("second") is None
    assert cache.get("first") == {"value": 1}
    assert cache.snapshot()["evictions"] == 1

    cache.set("short", "value", ttl_seconds=0.001, max_entries=3)
    sleep(0.005)
    assert cache.get("short") is None


def test_bounded_ttl_cache_returns_defensive_copies():
    cache = BoundedTTLCache()
    source = [{"content": "safe"}]
    cache.set("key", source, ttl_seconds=1, max_entries=2)
    first = cache.get("key")
    first[0]["content"] = "mutated"

    assert cache.get("key") == [{"content": "safe"}]


def test_bounded_ttl_cache_remains_bounded_under_concurrent_access():
    cache = BoundedTTLCache()

    def write_and_read(index: int):
        cache.set(index, {"index": index}, ttl_seconds=1, max_entries=25)
        return cache.get(index)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(write_and_read, range(100)))

    assert any(item is not None for item in results)
    assert cache.snapshot()["entries"] <= 25
