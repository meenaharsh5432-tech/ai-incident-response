import logging

from fastapi import Request, Response
from redis.exceptions import ConnectionError, TimeoutError
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

logger = logging.getLogger(__name__)


class OptionalRateLimiter:
    """Rate limiter that silently skips when Redis is unavailable."""

    def __init__(self, times: int, seconds: int):
        self._limiter = RateLimiter(times=times, seconds=seconds)

    async def __call__(self, request: Request, response: Response):
        if FastAPILimiter.redis is None:
            return
        try:
            await self._limiter(request, response)
        except (ConnectionError, TimeoutError):
            logger.warning("Rate limiter skipped because Redis is unavailable")
