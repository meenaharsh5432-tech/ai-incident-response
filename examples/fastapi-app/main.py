"""
Example FastAPI app — zero-instrumentation error capture.

Run:  python main.py
Then: curl http://localhost:8001/db-timeout
      curl http://localhost:8001/auth-failure
      curl -X POST http://localhost:8001/payment?amount=-5
      curl http://localhost:8001/null-pointer

Every unhandled error auto-appears in the incident dashboard.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import uvicorn
from fastapi import FastAPI

from incident_reporter import IncidentReporter

app = FastAPI(title="Example FastAPI Service", version="1.0.0")

reporter = IncidentReporter(
    api_url=os.getenv("INCIDENT_API_URL", "http://localhost:8001"),
    service_name="fastapi-example",
    environment="dev",
    api_key=os.getenv("INCIDENT_API_KEY"),
)

# One line: registers exception handler + ASGI middleware
reporter.setup_fastapi(app)


@app.get("/")
def root():
    return {"status": "ok", "service": "fastapi-example"}


@app.get("/db-timeout")
def db_timeout():
    # Simulate: PostgreSQL connection timed out
    raise TimeoutError("Connection to postgres timed out after 30s — pool exhausted")


@app.get("/auth-failure")
def auth_failure():
    # Simulate: downstream JWT validation failure
    raise PermissionError("JWT token expired: signature mismatch (HS256)")


@app.post("/payment")
def process_payment(amount: float = 0.0):
    # Simulate: business logic validation error
    if amount <= 0:
        raise ValueError(f"Invalid payment amount: {amount}. Must be positive.")
    return {"status": "charged", "amount": amount}


@app.get("/null-pointer")
def null_pointer():
    # Simulate: accessing attribute on None (Python's NullPointerException)
    user = None
    return {"name": user["name"]}  # type: ignore[index]  → TypeError


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9001, reload=False)
