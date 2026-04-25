import json
import logging
import time
from typing import Optional

import httpx
import redis

from app.config import get_settings
from app.models.incident import Incident, IncidentSeverity

logger = logging.getLogger(__name__)
settings = get_settings()

_redis: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


SYSTEM_PROMPT = """\
You are an expert backend engineer and SRE. Analyze the provided error and respond ONLY \
with valid JSON (no markdown, no extra text) matching this exact schema:
{
  "root_cause": "<one clear sentence>",
  "severity": "<critical|high|medium|low>",
  "steps": ["<step 1>", "<step 2>", "..."],
  "code_snippet": "<minimal code fix, or empty string>",
  "prevention": "<one sentence on how to prevent this>"
}

Severity guide:
  critical – system down, data loss, security breach
  high     – major feature broken, significant user impact
  medium   – partial functionality affected
  low      – minor issue, cosmetic, easily worked around"""


def _fallback(reason: str) -> dict:
    return {
        "root_cause": reason,
        "severity": "medium",
        "steps": ["Review the stack trace", "Check recent deployments", "Inspect application logs"],
        "code_snippet": "",
        "prevention": "Add structured logging and alerting around this code path.",
    }


def should_diagnose(incident: Incident) -> bool:
    r = get_redis()
    cooldown_key = f"dx:cooldown:{incident.id}"

    if r.get(cooldown_key):
        # Allow re-diagnosis only if occurrences spiked significantly
        prev_count = int(r.get(f"dx:count:{incident.id}") or 0)
        if prev_count > 0 and incident.occurrence_count < prev_count * settings.DIAGNOSIS_SPIKE_MULTIPLIER:
            return False

    return True


_CONN_FALLBACK = {
    "root_cause": "AI diagnosis temporarily unavailable",
    "steps": ["Check application logs", "Review stack trace manually"],
    "code_snippet": "",
    "severity": "medium",
}


def diagnose_incident(incident: Incident, error_message: str, stack_trace: str) -> dict:
    if not settings.GROQ_API_KEY:
        return _fallback("AI diagnosis unavailable — set GROQ_API_KEY in .env to enable.")

    user_content = (
        f"Service: {incident.service_name}\n"
        f"Error type: {incident.error_type}\n"
        f"Occurrences: {incident.occurrence_count}\n"
        f"Message: {error_message}\n"
        f"Stack trace:\n{stack_trace or '(not provided)'}"
    )
    request_payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    request_headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # RemoteProtocolError covers "Connection closed by server" (common on Render free tier)
    _conn_errors = (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError)

    def _post() -> dict:
        with httpx.Client(timeout=settings.GROQ_TIMEOUT) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=request_headers,
                json=request_payload,
            )
            response.raise_for_status()
            return response.json()

    try:
        try:
            result = _post()
        except _conn_errors as exc:
            logger.warning("Diagnosis connection error for incident %s (attempt 1), retrying in 5s: %s", incident.id, exc)
            time.sleep(5)
            try:
                result = _post()
            except _conn_errors as retry_exc:
                logger.warning("Diagnosis failed after retry for incident %s: %s", incident.id, retry_exc)
                return _CONN_FALLBACK

        raw = result["choices"][0]["message"]["content"].strip()
        diagnosis = _parse_json(raw)

        r = get_redis()
        r.setex(f"dx:cooldown:{incident.id}", settings.DIAGNOSIS_COOLDOWN_SECONDS, "1")
        r.set(f"dx:count:{incident.id}", incident.occurrence_count)

        return diagnosis

    except Exception as exc:
        logger.warning("Diagnosis failed for incident %s: %s", incident.id, exc)
        return _fallback(f"Diagnosis request failed: {exc}")


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Extract JSON object if wrapped in prose
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return _fallback("Could not parse structured response from LLM.")


SEVERITY_MAP = {
    "critical": IncidentSeverity.critical,
    "high": IncidentSeverity.high,
    "medium": IncidentSeverity.medium,
    "low": IncidentSeverity.low,
}
