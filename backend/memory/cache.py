"""
Redis cache manager for response caching, rate limiting, and session storage.
"""
import json
import hashlib
from typing import Any, Optional

import structlog

from backend.config import settings

logger = structlog.get_logger()

_redis_client = None


async def get_redis():
    """Get or create the Redis client.

    Uses redis.asyncio (bundled with the modern `redis` package) directly.
    The standalone `aioredis` package is incompatible with Python 3.11+
    (it redefines TimeoutError as a subclass of itself under the new
    asyncio/builtins TimeoutError unification), so it is intentionally
    not used here.
    """
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as redis_async
            _redis_client = redis_async.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            return None
    return _redis_client


def make_cache_key(messages: list, provider: str, model: str) -> str:
    """Generate a deterministic cache key for an LLM request."""
    content = json.dumps({
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "provider": provider,
        "model": model,
    }, sort_keys=True)
    return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"


async def get_cached_response(cache_key: str) -> Optional[dict]:
    """Retrieve a cached LLM response."""
    redis = await get_redis()
    if not redis:
        return None
    try:
        data = await redis.get(cache_key)
        if data:
            logger.info("Cache hit", key=cache_key[:20])
            return json.loads(data)
    except Exception as e:
        logger.warning("Cache get failed", error=str(e))
    return None


async def set_cached_response(cache_key: str, response: dict, ttl: int = 3600):
    """Cache an LLM response."""
    redis = await get_redis()
    if not redis:
        return
    try:
        await redis.setex(cache_key, ttl, json.dumps(response, default=str))
    except Exception as e:
        logger.warning("Cache set failed", error=str(e))


async def check_rate_limit(user_id: str, limit_per_minute: int = 60) -> bool:
    """
    Token bucket rate limiter.
    Returns True if request is allowed, False if rate limited.
    """
    redis = await get_redis()
    if not redis:
        return True  # Allow if Redis unavailable

    key = f"rate_limit:{user_id}:minute"
    try:
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        return current <= limit_per_minute
    except Exception as e:
        logger.warning("Rate limit check failed", error=str(e))
        return True


async def get_session_history(session_id: str) -> list:
    """Get conversation history for a session from Redis."""
    redis = await get_redis()
    if not redis:
        return []
    try:
        data = await redis.get(f"session:{session_id}")
        return json.loads(data) if data else []
    except Exception:
        return []


async def save_session_history(session_id: str, messages: list, ttl: int = 86400):
    """Save conversation history to Redis (24h TTL by default)."""
    redis = await get_redis()
    if not redis:
        return
    try:
        serializable = [{"role": m.role if hasattr(m, "role") else m["role"],
                        "content": m.content if hasattr(m, "content") else m["content"]}
                       for m in messages]
        await redis.setex(f"session:{session_id}", ttl, json.dumps(serializable))
    except Exception as e:
        logger.warning("Session save failed", error=str(e))


async def check_redis_health() -> bool:
    """Health check for Redis."""
    redis = await get_redis()
    if not redis:
        return False
    try:
        await redis.ping()
        return True
    except Exception:
        return False
