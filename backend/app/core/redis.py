"""Redis client configuration and utilities."""

from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    """
    Get a cached Redis client instance.

    Returns:
        Async Redis client
    """
    settings = get_settings()
    return redis.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
    )


async def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int, int]:
    """
    Check if a rate limit has been exceeded using sliding window.

    Args:
        key: Unique identifier for the rate limit (e.g., "api_key:{key_id}")
        limit: Maximum number of requests allowed in the window
        window_seconds: Time window in seconds (default: 60)

    Returns:
        Tuple of (allowed, remaining, reset_seconds)
        - allowed: True if request is allowed
        - remaining: Number of requests remaining in window
        - reset_seconds: Seconds until the window resets
    """
    client = get_redis_client()

    # Use a simple sliding window counter
    # Key format: ratelimit:{key}:{window_start}
    import time

    current_time = int(time.time())
    window_start = current_time - (current_time % window_seconds)
    rate_key = f"ratelimit:{key}:{window_start}"

    try:
        # Increment the counter
        current_count = await client.incr(rate_key)

        # Set expiry on first request in window
        if current_count == 1:
            await client.expire(rate_key, window_seconds + 1)

        # Calculate remaining and reset time
        remaining = max(0, limit - current_count)
        reset_seconds = window_seconds - (current_time % window_seconds)

        # Check if allowed
        allowed = current_count <= limit

        return allowed, remaining, reset_seconds

    except redis.RedisError:
        # If Redis is unavailable, allow the request (fail open)
        # Log this in production
        return True, limit, window_seconds


async def get_rate_limit_info(
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> dict:
    """
    Get rate limit information without incrementing.

    Returns:
        Dict with limit, remaining, and reset info
    """
    client = get_redis_client()

    import time

    current_time = int(time.time())
    window_start = current_time - (current_time % window_seconds)
    rate_key = f"ratelimit:{key}:{window_start}"

    try:
        current_count = await client.get(rate_key)
        current_count = int(current_count) if current_count else 0

        remaining = max(0, limit - current_count)
        reset_seconds = window_seconds - (current_time % window_seconds)

        return {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_seconds,
            "used": current_count,
        }

    except redis.RedisError:
        return {
            "limit": limit,
            "remaining": limit,
            "reset": window_seconds,
            "used": 0,
        }
