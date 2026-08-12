from services.rate_limiter import _SlidingWindowLimiter


def test_allows_up_to_max_requests():
    limiter = _SlidingWindowLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        allowed, _ = limiter.check("user1")
        assert allowed


def test_blocks_after_max_requests():
    limiter = _SlidingWindowLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("user1")
    allowed, retry_after = limiter.check("user1")
    assert not allowed
    assert retry_after is not None and retry_after > 0


def test_different_keys_independent():
    limiter = _SlidingWindowLimiter(max_requests=1, window_seconds=60)
    allowed1, _ = limiter.check("user1")
    allowed2, _ = limiter.check("user2")
    assert allowed1 and allowed2


def test_window_resets_after_expiry():
    limiter = _SlidingWindowLimiter(max_requests=1, window_seconds=0.05)
    allowed1, _ = limiter.check("user1")
    assert allowed1
    import time

    time.sleep(0.1)
    allowed2, _ = limiter.check("user1")
    assert allowed2
