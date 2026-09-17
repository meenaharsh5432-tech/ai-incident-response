"""Redis outages must not prevent diagnosis or erase a successful AI response."""
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi_limiter import FastAPILimiter
from redis.exceptions import ConnectionError, TimeoutError


APP = Path(__file__).resolve().parents[1] / "backend" / "app"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("failure", [ConnectionError("DNS unavailable"), TimeoutError("Timed out")])
def test_limiter_allows_request_during_redis_outage(monkeypatch, failure):
    module = load_module("limiter_under_test", APP / "limiter.py")
    monkeypatch.setattr(FastAPILimiter, "redis", MagicMock())
    limiter = module.OptionalRateLimiter(times=10, seconds=60)
    limiter._limiter = AsyncMock(side_effect=failure)
    asyncio.run(limiter(MagicMock(), MagicMock()))
    limiter._limiter.assert_awaited_once()


def test_limiter_preserves_rate_limit_rejection(monkeypatch):
    module = load_module("limiter_under_test", APP / "limiter.py")
    monkeypatch.setattr(FastAPILimiter, "redis", MagicMock())
    limiter = module.OptionalRateLimiter(times=10, seconds=60)
    limiter._limiter = AsyncMock(side_effect=HTTPException(status_code=429))
    with pytest.raises(HTTPException) as error:
        asyncio.run(limiter(MagicMock(), MagicMock()))
    assert error.value.status_code == 429


def test_limiter_skips_when_startup_disabled_it(monkeypatch):
    module = load_module("limiter_under_test", APP / "limiter.py")
    monkeypatch.setattr(FastAPILimiter, "redis", None)
    limiter = module.OptionalRateLimiter(times=10, seconds=60)
    limiter._limiter = AsyncMock()
    asyncio.run(limiter(MagicMock(), MagicMock()))
    limiter._limiter.assert_not_awaited()


@pytest.mark.parametrize("operation", ["setex", "set"])
def test_successful_diagnosis_survives_cache_write_failure(monkeypatch, operation):
    # Isolate the service from database setup and local credentials.
    config = ModuleType("app.config")
    config.get_settings = lambda: SimpleNamespace(
        GROQ_API_KEY="test-key", GROQ_TIMEOUT=1, DIAGNOSIS_COOLDOWN_SECONDS=60,
    )
    models = ModuleType("app.models.incident")
    models.Incident = object
    models.IncidentSeverity = SimpleNamespace(
        critical="critical", high="high", medium="medium", low="low",
    )
    monkeypatch.setitem(sys.modules, "app.config", config)
    monkeypatch.setitem(sys.modules, "app.models.incident", models)
    module = load_module("diagnosis_under_test", APP / "services" / "diagnosis_service.py")
    expected = {"root_cause": "Database pool exhausted", "severity": "high", "steps": ["Increase pool size"]}
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.return_value.json.return_value = {
        "choices": [{"message": {"content": json.dumps(expected)}}],
    }
    monkeypatch.setattr(module.httpx, "Client", MagicMock(return_value=client))
    cache = MagicMock()
    getattr(cache, operation).side_effect = ConnectionError("DNS unavailable")
    monkeypatch.setattr(module, "get_redis", lambda: cache)
    incident = SimpleNamespace(id=8, service_name="api", error_type="Timeout", occurrence_count=3)
    assert module.diagnose_incident(incident, "Pool timeout", "trace") == expected
