"""
Example Flask app — zero-instrumentation error capture.

Run:  python app.py
Then: curl http://localhost:8002/db-timeout
      curl http://localhost:8002/auth-failure
      curl -X POST -H "Content-Type: application/json" \
           -d '{"amount": -1}' http://localhost:8002/payment
      curl http://localhost:8002/null-pointer

Every unhandled error auto-appears in the incident dashboard.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from flask import Flask, jsonify, request

from incident_reporter import IncidentReporter

app = Flask(__name__)

reporter = IncidentReporter(
    api_url=os.getenv("INCIDENT_API_URL", "http://localhost:8001"),
    service_name="flask-example",
    environment="dev",
    api_key=os.getenv("INCIDENT_API_KEY"),
)

# One line: registers @app.errorhandler(Exception) for automatic capture
reporter.register_flask_app(app)


@app.route("/")
def index():
    return jsonify({"status": "ok", "service": "flask-example"})


@app.route("/db-timeout")
def db_timeout():
    # Simulate: MySQL connection pool exhausted
    raise TimeoutError("MySQL connection pool exhausted — all 20 connections in use")


@app.route("/auth-failure")
def auth_failure():
    # Simulate: OAuth2 token validation failure
    raise PermissionError("OAuth2 token validation failed: token revoked by user")


@app.route("/payment", methods=["POST"])
def process_payment():
    # Simulate: invalid business input
    data = request.get_json() or {}
    amount = data.get("amount", 0)
    if amount <= 0:
        raise ValueError(f"Invalid payment amount: {amount}. Must be positive.")
    return jsonify({"status": "charged", "amount": amount})


@app.route("/null-pointer")
def null_pointer():
    # Simulate: None config lookup
    config = None
    return jsonify({"db": config["database_url"]})  # type: ignore[index]  → TypeError


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=9002)
