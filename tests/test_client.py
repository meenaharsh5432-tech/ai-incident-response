import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from incident_reporter.client import IncidentReporter


@pytest.fixture
def reporter(tmp_path):
    r = IncidentReporter(
        api_url="http://localhost:8000",
        service_name="test-service",
        flush_interval=9999,  # prevent auto-flush during tests
        fallback_log_path=str(tmp_path / "fallback.log"),
    )
    yield r
    r.shutdown()


def test_capture_queues_error(reporter):
    exc = ValueError("test error")
    reporter.capture(exc, stack_trace="tb here", metadata={"k": "v"})

    assert len(reporter._queue) == 1
    p = reporter._queue[0]
    assert p["error_type"] == "ValueError"
    assert p["message"] == "test error"
    assert p["stack_trace"] == "tb here"
    assert p["metadata"] == {"k": "v"}
    assert p["service_name"] == "test-service"


def test_capture_never_crashes(reporter):
    reporter.capture(None)  # should not raise
    reporter.capture("not an exception")  # type: ignore


def test_capture_uses_exception_traceback(reporter):
    try:
        raise RuntimeError("oops")
    except RuntimeError as e:
        reporter.capture(e)

    assert len(reporter._queue) == 1
    assert "RuntimeError" in reporter._queue[0]["stack_trace"]


def test_send_with_retry_success(reporter):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 1, "incident_id": 1}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = reporter._send_with_retry({"error_type": "Error", "message": "test"})

    assert mock_post.call_count == 1
    assert result == {"id": 1, "incident_id": 1}


def test_send_with_retry_exponential_backoff(reporter):
    reporter.max_retries = 3

    with patch("requests.post", side_effect=ConnectionError("refused")):
        with patch("time.sleep") as mock_sleep:
            reporter._send_with_retry({"error_type": "Error", "message": "test"})

    assert mock_sleep.call_count == 3
    mock_sleep.assert_any_call(1)   # 2^0
    mock_sleep.assert_any_call(2)   # 2^1
    mock_sleep.assert_any_call(4)   # 2^2


def test_fallback_written_after_all_retries(reporter):
    reporter.max_retries = 1

    with patch("requests.post", side_effect=ConnectionError("down")):
        with patch("time.sleep"):
            reporter._send_with_retry({"error_type": "DBError", "message": "conn failed"})

    assert os.path.exists(reporter.fallback_log_path)
    with open(reporter.fallback_log_path) as f:
        entry = json.loads(f.readline())
    assert entry["error_type"] == "DBError"
    assert "timestamp" in entry


def test_api_key_sent_in_header(reporter):
    reporter.api_key = "secret-key-123"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        reporter._send_with_retry({"error_type": "E", "message": "m"})

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-API-Key"] == "secret-key-123"


def test_flush_clears_queue(reporter):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}

    reporter.capture(ValueError("e1"))
    reporter.capture(ValueError("e2"))
    assert len(reporter._queue) == 2

    with patch("requests.post", return_value=mock_resp):
        reporter._flush()

    assert len(reporter._queue) == 0


def test_flush_empty_queue_is_noop(reporter):
    with patch("requests.post") as mock_post:
        reporter._flush()
    mock_post.assert_not_called()
