import functools
import inspect
from typing import Optional


def capture_errors(reporter=None, service_name: Optional[str] = None):
    """Decorator that captures exceptions and reports them, then re-raises.

    Usage:
        @capture_errors(reporter)
        def my_function(): ...

        @capture_errors          # reporter=None, silently queues nothing
        def my_function(): ...
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    _report(exc, func, args, kwargs, reporter)
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    _report(exc, func, args, kwargs, reporter)
                    raise
            return sync_wrapper

    # Support both @capture_errors and @capture_errors(reporter)
    if callable(reporter):
        func = reporter
        reporter = None
        return decorator(func)

    return decorator


def _report(exc, func, args, kwargs, reporter) -> None:
    if reporter is None:
        return
    try:
        reporter.capture(exc, metadata={
            "function": func.__name__,
            "module": func.__module__,
            "args": _sanitize_args(args, kwargs),
        })
    except Exception:
        pass  # never crash the host application


_SENSITIVE_KEYS = frozenset({"password", "token", "secret", "key", "auth", "credential", "passwd"})


def _sanitize_args(args, kwargs) -> dict:
    safe_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(k, str) and any(s in k.lower() for s in _SENSITIVE_KEYS):
            safe_kwargs[k] = "***REDACTED***"
        else:
            try:
                import json
                json.dumps(v)
                safe_kwargs[k] = v
            except (TypeError, ValueError):
                safe_kwargs[k] = repr(v)
    return {"kwargs": safe_kwargs, "positional_count": len(args)}
