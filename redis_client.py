#file : redis_client.py



import os
import redis
import json

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=2
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False


def get_cache(key):
    if not REDIS_AVAILABLE:
        return None

    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def set_cache(key, value, ttl=60):
    if not REDIS_AVAILABLE:
        return

    try:
        redis_client.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass


def delete_cache(key):
    if not REDIS_AVAILABLE:
        return

    try:
        redis_client.delete(key)
    except Exception:
        pass