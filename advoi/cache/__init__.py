"""Shared caches for low-latency reads."""

from advoi.cache.redis_client import get_redis, redis_available

__all__ = ["get_redis", "redis_available"]