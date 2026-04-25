"""
Framework-specific middleware classes.

Flask usage:
    from incident_reporter import flask_middleware
    app.wsgi_app = flask_middleware(app.wsgi_app, reporter)

Django usage:
    # In settings.py, add 'incident_reporter.middleware.DjangoMiddleware' to MIDDLEWARE.
    # Before app startup, call: DjangoMiddleware.configure(reporter)
"""


class FlaskMiddleware:
    """WSGI middleware wrapper for Flask.

    Catches exceptions that propagate through the WSGI layer.
    For complete coverage (Flask catches most exceptions internally),
    also call reporter.register_flask_app(app).
    """

    def __init__(self, wsgi_app, reporter):
        self.wsgi_app = wsgi_app
        self.reporter = reporter

    def __call__(self, environ, start_response):
        try:
            return self.wsgi_app(environ, start_response)
        except Exception as exc:
            try:
                self.reporter.capture(exc, metadata={
                    "path": environ.get("PATH_INFO", ""),
                    "method": environ.get("REQUEST_METHOD", ""),
                    "query_string": environ.get("QUERY_STRING", ""),
                })
            except Exception:
                pass
            raise


class DjangoMiddleware:
    """Django middleware that captures unhandled exceptions via process_exception.

    Add 'incident_reporter.middleware.DjangoMiddleware' to Django's MIDDLEWARE
    setting, then call DjangoMiddleware.configure(reporter) at app startup.
    """

    _reporter = None

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exc):
        reporter = DjangoMiddleware._reporter
        if reporter is None:
            return None
        try:
            user_id = None
            if hasattr(request, "user") and hasattr(request.user, "id"):
                try:
                    user_id = str(request.user.id)
                except Exception:
                    pass

            reporter.capture(exc, metadata={
                "path": request.path,
                "method": request.method,
                "user_id": user_id,
            })
        except Exception:
            pass
        return None  # let Django's normal exception handling continue

    @classmethod
    def configure(cls, reporter) -> None:
        cls._reporter = reporter
