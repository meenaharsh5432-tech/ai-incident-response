from fastapi import Request, Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter


class OptionalRateLimiter:
    """Rate limiter that silently skips when Redis is unavailable."""

    def __init__(self, times: int, seconds: int):
        self._limiter = RateLimiter(times=times, seconds=seconds)

    async def __call__(self, request: Request, response: Response):
        if FastAPILimiter.redis is None:
            return
        await self._limiter(request, response)
