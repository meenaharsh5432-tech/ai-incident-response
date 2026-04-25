#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_demo.sh — One-command demo: starts all services and floods them with traffic
#
# Prerequisites:
#   • pip install -e .                       (Python SDK)
#   • pip install fastapi uvicorn flask requests  (example app deps)
#   • cd incident-reporter-node && npm install   (Node SDK)
#   • cd examples/node-express-app && npm install
#   • Backend + PostgreSQL already running (docker compose up -d)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${GREEN}[demo]${NC} $*"; }
warn() { echo -e "${YELLOW}[demo]${NC} $*"; }
err()  { echo -e "${RED}[demo]${NC} $*" >&2; }

# ─── Cleanup on exit ─────────────────────────────────────────────────────────
PIDS=()
cleanup() {
    log "Shutting down demo processes..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    log "Done."
}
trap cleanup EXIT INT TERM

# ─── Check main backend ───────────────────────────────────────────────────────
log "Checking main backend at http://localhost:8000..."
if ! curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    warn "Main backend not responding at :8000."
    warn "Starting it now (requires PostgreSQL on :5432)..."
    cd backend
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    PIDS+=($!)
    cd "$SCRIPT_DIR"
    sleep 4
else
    log "Main backend already running."
fi

# ─── Start example FastAPI app ────────────────────────────────────────────────
log "Starting FastAPI example on :8001..."
cd examples/fastapi-app
python main.py &
PIDS+=($!)
cd "$SCRIPT_DIR"

# ─── Start example Flask app ──────────────────────────────────────────────────
log "Starting Flask example on :8002..."
cd examples/flask-app
python app.py &
PIDS+=($!)
cd "$SCRIPT_DIR"

# ─── Start example Express app ────────────────────────────────────────────────
log "Starting Express example on :8003..."
if ! command -v node &>/dev/null; then
    warn "Node.js not found — skipping Express example."
else
    cd examples/node-express-app
    # Install express dependency if not present
    if [ ! -d "node_modules" ]; then
        warn "Installing express..."
        npm install --silent
    fi
    node index.js &
    PIDS+=($!)
    cd "$SCRIPT_DIR"
fi

# ─── Wait for apps to boot ────────────────────────────────────────────────────
log "Waiting for example apps to boot..."
sleep 3

for port in 9001 9002 9003; do
    if curl -sf "http://localhost:${port}/" >/dev/null 2>&1; then
        log "  :${port} OK"
    else
        warn "  :${port} not responding (may still be starting or skipped)"
    fi
done

# ─── Run traffic generator ───────────────────────────────────────────────────
log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "  Running traffic generator (60s, 5 req/s)..."
log "  Dashboard: http://localhost:3002"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""

python traffic_generator.py --duration 60 --rps 5

log ""
log "Demo complete. Example apps are still running — Ctrl+C to stop."
log "Dashboard: http://localhost:3002"

# Keep running so the apps stay up for manual exploration
wait
