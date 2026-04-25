from unittest.mock import MagicMock

import pytest

from incident_reporter.middleware import DjangoMiddleware, FlaskMiddleware


# ──────────────────────────────────────────────
# Flask Middleware
# ──────────────────────────────────────────────

def test_flask_middleware_passes_through_cleanly():
    reporter = MagicMock()
    wsgi_app = MagicMock(return_value=iter([b"OK"]))

    mw = FlaskMiddleware(wsgi_app, reporter)
    environ = {"PATH_INFO": "/test", "REQUEST_METHOD": "GET"}

    mw(environ, MagicMock())

    wsgi_app.assert_called_once()
    reporter.capture.assert_not_called()


def test_flask_middleware_captures_and_reraises():
    reporter = MagicMock()
    exc = RuntimeError("DB connection failed")
    wsgi_app = MagicMock(side_effect=exc)

    mw = FlaskMiddleware(wsgi_app, reporter)
    environ = {"PATH_INFO": "/users", "REQUEST_METHOD": "POST"}

    with pytest.raises(RuntimeError, match="DB connection failed"):
        mw(environ, MagicMock())

    reporter.capture.assert_called_once()
    reported_exc = reporter.capture.call_args[0][0]
    assert reported_exc is exc


def test_flask_middleware_includes_request_metadata():
    reporter = MagicMock()
    wsgi_app = MagicMock(side_effect=ValueError("oops"))

    mw = FlaskMiddleware(wsgi_app, reporter)
    environ = {
        "PATH_INFO": "/api/pay",
        "REQUEST_METHOD": "POST",
        "QUERY_STRING": "debug=1",
    }

    with pytest.raises(ValueError):
        mw(environ, MagicMock())

    meta = reporter.capture.call_args[1]["metadata"]
    assert meta["path"] == "/api/pay"
    assert meta["method"] == "POST"


def test_flask_middleware_reporter_crash_does_not_swallow_exception():
    reporter = MagicMock()
    reporter.capture.side_effect = Exception("reporter blew up")
    wsgi_app = MagicMock(side_effect=RuntimeError("real error"))

    mw = FlaskMiddleware(wsgi_app, reporter)

    # The real error should still propagate even if the reporter crashes
    with pytest.raises(RuntimeError, match="real error"):
        mw({}, MagicMock())


# ──────────────────────────────────────────────
# Django Middleware
# ──────────────────────────────────────────────

def _make_django_request(path="/test", method="GET", user_id=None):
    req = MagicMock()
    req.path = path
    req.method = method
    if user_id is not None:
        req.user.id = user_id
    else:
        del req.user.id  # simulate anonymous user without id
    return req


def test_django_process_exception_calls_reporter():
    reporter = MagicMock()
    DjangoMiddleware.configure(reporter)

    mw = DjangoMiddleware(MagicMock())
    exc = ValueError("query failed")
    result = mw.process_exception(_make_django_request(), exc)

    assert result is None  # Django should continue normal handling
    reporter.capture.assert_called_once()
    assert reporter.capture.call_args[0][0] is exc


def test_django_process_exception_without_reporter():
    DjangoMiddleware.configure(None)

    mw = DjangoMiddleware(MagicMock())
    exc = ValueError("no reporter set")
    result = mw.process_exception(_make_django_request(), exc)

    assert result is None  # should not crash


def test_django_process_exception_metadata():
    reporter = MagicMock()
    DjangoMiddleware.configure(reporter)

    mw = DjangoMiddleware(MagicMock())
    req = _make_django_request(path="/api/orders", method="DELETE", user_id=99)
    mw.process_exception(req, RuntimeError("db error"))

    meta = reporter.capture.call_args[1]["metadata"]
    assert meta["path"] == "/api/orders"
    assert meta["method"] == "DELETE"
    assert meta["user_id"] == "99"


def test_django_call_delegates_to_get_response():
    reporter = MagicMock()
    DjangoMiddleware.configure(reporter)

    fake_response = MagicMock(status_code=200)
    get_response = MagicMock(return_value=fake_response)
    mw = DjangoMiddleware(get_response)

    result = mw(_make_django_request())
    assert result is fake_response
    get_response.assert_called_once()
