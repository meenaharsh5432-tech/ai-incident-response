import json
import logging
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class IncidentReporter:
    def __init__(
        self,
        api_url: str,
        service_name: str,
        environment: str = "prod",
        api_key: Optional[str] = None,
        flush_interval: float = 5.0,
        max_retries: int = 3,
        fallback_log_path: str = "incident_fallback.log",
    ):
        self.api_url = api_url.rstrip("/")
        self.service_name = service_name
        self.environment = environment
        self.api_key = api_key
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        self.fallback_log_path = fallback_log_path

        self._queue: List[Dict] = []
        self._lock = threading.Lock()
        self._shutdown = threading.Event()

        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def capture(
        self,
        error: Exception,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            if stack_trace is None:
                if error is not None and hasattr(error, "__traceback__"):
                    stack_trace = "".join(
                        traceback.format_exception(type(error), error, error.__traceback__)
                    )
                else:
                    current = traceback.format_exc()
                    stack_trace = "" if current == "NoneType: None\n" else current

            payload = {
                "error_type": type(error).__name__ if error is not None else "UnknownError",
                "message": str(error) if error is not None else "Unknown error",
                "stack_trace": stack_trace,
                "service_name": self.service_name,
                "environment": self.environment,
                "metadata": metadata or {},
            }
            with self._lock:
                self._queue.append(payload)
        except Exception:
            pass  # never crash the host application

    def _flush_loop(self) -> None:
        while not self._shutdown.wait(self.flush_interval):
            self._flush()

    def _flush(self) -> None:
        with self._lock:
            if not self._queue:
                return
            batch, self._queue = self._queue[:], []

        for payload in batch:
            self._send_with_retry(payload)

    def _send_with_retry(self, payload: Dict) -> Optional[Dict]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.api_url}/api/errors",
                    json=payload,
                    headers=headers,
                    timeout=5,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # 1s, 2s, 4s
                else:
                    self._write_fallback(payload)
        return None

    def _write_fallback(self, payload: Dict) -> None:
        try:
            entry = {"timestamp": datetime.utcnow().isoformat(), **payload}
            with open(self.fallback_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def shutdown(self) -> None:
        self._shutdown.set()
        self._flush_thread.join(timeout=10)
        self._flush()

    @property
    def fastapi_middleware(self):
        """Raw ASGI middleware class — outermost layer, catches low-level exceptions."""
        _reporter = self

        class _IncidentReporterMiddleware:
            def __init__(self, app):
                self.app = app

            async def __call__(self, scope, receive, send):
                if scope["type"] != "http":
                    await self.app(scope, receive, send)
                    return
                try:
                    await self.app(scope, receive, send)
                except Exception as exc:
                    try:
                        _reporter.capture(exc, metadata={
                            "path": scope.get("path", ""),
                            "method": scope.get("method", ""),
                        })
                    except Exception:
                        pass
                    raise

        return _IncidentReporterMiddleware

    def setup_fastapi(self, app) -> None:
        """Register both exception handler and ASGI middleware on a FastAPI app.

        This is the recommended integration — the exception handler captures
        application-level errors that FastAPI converts to 500 responses, while
        the ASGI middleware catches anything that escapes entirely.
        """
        from fastapi.responses import JSONResponse

        reporter = self

        @app.exception_handler(Exception)
        async def _catch_all(request, exc):
            try:
                reporter.capture(exc, metadata={
                    "path": str(request.url.path),
                    "method": request.method,
                })
            except Exception:
                pass
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        app.add_middleware(reporter.fastapi_middleware)

    def register_flask_app(self, flask_app) -> None:
        """Register a catch-all error handler on a Flask app."""
        reporter = self

        @flask_app.errorhandler(Exception)
        def _catch_all(exc):
            try:
                from flask import request as flask_request
                reporter.capture(exc, metadata={
                    "path": flask_request.path,
                    "method": flask_request.method,
                })
            except Exception:
                pass
            return {"error": "Internal server error", "detail": str(exc)}, 500
