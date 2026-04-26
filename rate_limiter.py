# file: rate_limiter.py

import time
from redis_client import redis_client, REDIS_AVAILABLE

RATE_LIMIT = 3        # max requests
WINDOW_SECONDS = 1    # per second


def is_rate_limited(user_id: int) -> bool:
    if not REDIS_AVAILABLE:
        return False  # fallback

    key = f"rate:{user_id}"

    try:
        count = redis_client.incr(key)

        if count == 1:
            redis_client.expire(key, WINDOW_SECONDS)

        return count > RATE_LIMIT

    except Exception:
        return False