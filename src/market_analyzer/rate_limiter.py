"""Per-user and global rate limiting for tailoring requests."""

import time
from collections import defaultdict

# Per-user cooldown in seconds
USER_COOLDOWN = 10

# Global rate limit: max requests in a rolling window
GLOBAL_MAX_REQUESTS = 30
GLOBAL_WINDOW_SECONDS = 60

_user_last_request: dict[int, float] = defaultdict(float)
_global_requests: list[float] = []


def check_rate_limit(user_id: int) -> tuple[bool, str]:
    """Check if a tailoring request is allowed.

    Returns:
        (allowed, message) — if not allowed, message explains why.
    """
    now = time.time()

    # Per-user cooldown
    elapsed = now - _user_last_request[user_id]
    if elapsed < USER_COOLDOWN:
        wait = int(USER_COOLDOWN - elapsed) + 1
        return False, f"Please wait {wait} seconds and try again."

    # Global rolling window
    global _global_requests
    _global_requests = [t for t in _global_requests if now - t < GLOBAL_WINDOW_SECONDS]
    if len(_global_requests) >= GLOBAL_MAX_REQUESTS:
        return False, "The service is busy. Please try again in a minute."

    # Record this request
    _user_last_request[user_id] = now
    _global_requests.append(now)

    return True, ""


def reset():
    """Reset all rate limit state (for testing)."""
    global _global_requests
    _user_last_request.clear()
    _global_requests = []
