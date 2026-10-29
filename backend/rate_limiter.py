"""A tiny in-memory rate limiter (sliding window) to stop accidental request floods."""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max(1, max_requests)
        self.window = window_seconds
        self._hits = defaultdict(deque)  # key (e.g. IP address) -> times of recent requests
        self._lock = threading.Lock()    # Flask may handle requests in several threads

    def check(self, key):
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:  # forget requests outside the window
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False, int(self.window - (now - hits[0])) + 1
            hits.append(now)
            return True, 0