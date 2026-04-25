from .client import IncidentReporter
from .decorators import capture_errors
from .middleware import DjangoMiddleware, FlaskMiddleware


def flask_middleware(wsgi_app, reporter):
    """Convenience wrapper: app.wsgi_app = flask_middleware(app.wsgi_app, reporter)"""
    return FlaskMiddleware(wsgi_app, reporter)


__all__ = [
    "IncidentReporter",
    "capture_errors",
    "FlaskMiddleware",
    "DjangoMiddleware",
    "flask_middleware",
]
