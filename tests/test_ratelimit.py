"""Rate limiter: window maths, client identity, and the FastAPI dependency.

Pure-Python — builds its own tiny app, so no Qdrant/LLM and no shared state
with the real endpoints' limiters.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.ratelimit import SlidingWindowLimiter, rate_limited


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_window_allows_then_blocks_then_recovers() -> None:
    clock = FakeClock()
    lim = SlidingWindowLimiter(2, 60.0, clock=clock)
    assert lim.hit("a") == 0.0
    assert lim.hit("a") == 0.0
    wait = lim.hit("a")
    assert 0 < wait <= 60.0  # blocked, told how long to wait
    clock.now += 61
    assert lim.hit("a") == 0.0  # window slid past the old hits


def test_keys_are_independent() -> None:
    lim = SlidingWindowLimiter(1, 60.0, clock=FakeClock())
    assert lim.hit("a") == 0.0
    assert lim.hit("b") == 0.0
    assert lim.hit("a") > 0


def test_blocked_hits_do_not_extend_the_block() -> None:
    clock = FakeClock()
    lim = SlidingWindowLimiter(1, 60.0, clock=clock)
    lim.hit("a")
    for _ in range(50):
        lim.hit("a")  # hammering while blocked must not push the reset out
    clock.now += 60.1
    assert lim.hit("a") == 0.0


def test_idle_keys_are_pruned() -> None:
    clock = FakeClock()
    lim = SlidingWindowLimiter(5, 60.0, max_keys=3, clock=clock)
    for k in "abc":
        lim.hit(k)
    clock.now += 120
    lim.hit("d")
    lim.hit("e")  # over max_keys → idle a/b/c dropped
    assert set(lim._hits) <= {"d", "e"}


def _app(per_minute: int, hops: int = 1) -> TestClient:
    app = FastAPI()

    @app.get("/x", dependencies=[Depends(rate_limited(per_minute, hops))])
    def x() -> dict:
        return {"ok": True}

    return TestClient(app)


def test_dependency_returns_429_with_retry_after() -> None:
    c = _app(2)
    assert c.get("/x").status_code == 200
    assert c.get("/x").status_code == 200
    r = c.get("/x")
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1
    assert "Too many requests" in r.json()["detail"]


def test_zero_disables_the_limit() -> None:
    c = _app(0)
    assert all(c.get("/x").status_code == 200 for _ in range(30))


def test_forwarded_for_uses_the_trusted_rightmost_entry() -> None:
    c = _app(1)
    # Same real client (rightmost), different spoofed leftmost entries → still one bucket.
    assert c.get("/x", headers={"X-Forwarded-For": "1.1.1.1, 9.9.9.9"}).status_code == 200
    assert c.get("/x", headers={"X-Forwarded-For": "2.2.2.2, 9.9.9.9"}).status_code == 429
    # A different real client gets its own bucket.
    assert c.get("/x", headers={"X-Forwarded-For": "1.1.1.1, 8.8.8.8"}).status_code == 200


def test_short_forwarded_for_is_ignored() -> None:
    # An XFF with fewer entries than trusted hops is insufficient/untrusted →
    # the socket peer keys the bucket, never a spoofable leftmost entry.
    c = _app(1)
    assert c.get("/x", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert c.get("/x", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429


def test_proxy_identity_header_is_ignored_without_a_token() -> None:
    # Default configuration (no PROXY_IDENTITY_TOKEN): a caller can set our
    # proxy's headers directly; they must not change client identity — the
    # XFF rightmost entry (or the socket peer) rules as before.
    c = _app(1)
    h = {"X-Reikun-Client": "1.1.1.1", "X-Reikun-Proxy": "secret"}
    assert c.get("/x", headers=h).status_code == 200
    assert c.get("/x", headers=h).status_code == 429
    assert c.get("/x", headers={**h, "X-Forwarded-For": "9.9.9.9"}).status_code == 200


def test_signed_proxy_identity_header_names_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.ratelimit as rl

    monkeypatch.setattr(rl, "PROXY_IDENTITY_TOKEN", "secret")
    c = _app(1)
    h = {"X-Reikun-Client": "1.1.1.1", "X-Reikun-Proxy": "secret", "X-Forwarded-For": "1.1.1.1, 8.8.8.8"}
    # The signed header wins over XFF entirely (its rightmost entry is the
    # proxy's own egress address, shared by every visitor behind the proxy).
    assert c.get("/x", headers=h).status_code == 200
    assert c.get("/x", headers=h).status_code == 429
    # A different stated client gets its own bucket — XFF can't fake it.
    other = {**h, "X-Reikun-Client": "2.2.2.2"}
    assert c.get("/x", headers=other).status_code == 200


def test_wrong_proxy_token_falls_back_to_xff(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.ratelimit as rl

    monkeypatch.setattr(rl, "PROXY_IDENTITY_TOKEN", "secret")
    c = _app(1)
    good = {"X-Reikun-Client": "1.1.1.1", "X-Reikun-Proxy": "secret"}
    assert c.get("/x", headers=good).status_code == 200
    assert c.get("/x", headers=good).status_code == 429
    # Wrong token: unsigned path — identity reads XFF rightmost (8.8.8.8), a separate bucket.
    bad = {**good, "X-Reikun-Proxy": "wrong", "X-Forwarded-For": "8.8.8.8"}
    assert c.get("/x", headers=bad).status_code == 200
