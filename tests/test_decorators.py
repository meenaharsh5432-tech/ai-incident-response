from unittest.mock import MagicMock

import pytest

from incident_reporter.decorators import capture_errors


@pytest.fixture
def reporter():
    return MagicMock()


def test_reraises_original_exception(reporter):
    @capture_errors(reporter)
    def failing():
        raise ValueError("original message")

    with pytest.raises(ValueError, match="original message"):
        failing()


def test_calls_reporter_capture(reporter):
    @capture_errors(reporter)
    def failing():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        failing()

    reporter.capture.assert_called_once()
    exc_arg = reporter.capture.call_args[0][0]
    assert isinstance(exc_arg, RuntimeError)


def test_metadata_includes_function_name(reporter):
    @capture_errors(reporter)
    def my_special_function():
        raise TypeError("type mismatch")

    with pytest.raises(TypeError):
        my_special_function()

    meta = reporter.capture.call_args[1]["metadata"]
    assert meta["function"] == "my_special_function"


def test_success_does_not_call_reporter(reporter):
    @capture_errors(reporter)
    def works(x, y):
        return x + y

    result = works(2, 3)
    assert result == 5
    reporter.capture.assert_not_called()


def test_no_reporter_no_crash():
    @capture_errors
    def failing():
        raise ValueError("test")

    with pytest.raises(ValueError):
        failing()  # should not raise AttributeError or anything else


def test_sensitive_kwargs_redacted(reporter):
    @capture_errors(reporter)
    def login(username, password="secret123"):
        raise RuntimeError("auth failed")

    with pytest.raises(RuntimeError):
        login("alice", password="secret123")

    meta = reporter.capture.call_args[1]["metadata"]
    assert meta["args"]["kwargs"]["password"] == "***REDACTED***"


@pytest.mark.asyncio
async def test_async_function_reraises(reporter):
    @capture_errors(reporter)
    async def async_failing():
        raise ValueError("async error")

    with pytest.raises(ValueError, match="async error"):
        await async_failing()

    reporter.capture.assert_called_once()


@pytest.mark.asyncio
async def test_async_success_no_capture(reporter):
    @capture_errors(reporter)
    async def async_ok():
        return 42

    result = await async_ok()
    assert result == 42
    reporter.capture.assert_not_called()
