"""
Traffic generator — floods the three example apps with realistic traffic.

Usage:
    python traffic_generator.py [--duration 60] [--rps 5]

30% of requests are designed to trigger errors (realistic production ratio).
"""
import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import NamedTuple

import requests

SERVICES = {
    "fastapi-example": {
        "base": "http://localhost:9001",
        "happy_paths": ["/"],
        "error_paths": ["/db-timeout", "/auth-failure", "/null-pointer"],
        "post_paths": [("/payment", {"amount": -5}), ("/payment", {"amount": 50})],
    },
    "flask-example": {
        "base": "http://localhost:9002",
        "happy_paths": ["/"],
        "error_paths": ["/db-timeout", "/auth-failure", "/null-pointer"],
        "post_paths": [
            ("/payment", {"amount": -1}),
            ("/payment", {"amount": 100}),
        ],
    },
    "express-example": {
        "base": "http://localhost:9003",
        "happy_paths": ["/"],
        "error_paths": ["/json-parse-error", "/db-connection", "/auth-expired"],
        "post_paths": [],
    },
}


class Result(NamedTuple):
    service: str
    path: str
    status: int
    is_error: bool
    latency_ms: float


def _hit(service_name: str, cfg: dict, force_error: bool) -> Result:
    if force_error:
        path = random.choice(cfg["error_paths"])
        url = cfg["base"] + path
        method = "GET"
        body = None
    elif cfg["post_paths"] and random.random() < 0.3:
        path, body = random.choice(cfg["post_paths"])
        url = cfg["base"] + path
        method = "POST"
    else:
        path = random.choice(cfg["happy_paths"])
        url = cfg["base"] + path
        method = "GET"
        body = None

    t0 = time.monotonic()
    try:
        if method == "POST":
            resp = requests.post(url, json=body, timeout=5)
        else:
            resp = requests.get(url, timeout=5)
        status = resp.status_code
    except requests.exceptions.ConnectionError:
        status = 0
    except Exception:
        status = -1
    latency_ms = (time.monotonic() - t0) * 1000

    is_error = status == 0 or status >= 500
    return Result(service_name, path, status, is_error, latency_ms)


def run(duration_s: int, rps: int) -> None:
    interval = 1.0 / rps
    deadline = time.monotonic() + duration_s

    results: list[Result] = []
    total = 0
    errors = 0
    unreachable = set()

    print(f"\nGenerating traffic for {duration_s}s at {rps} req/s across {len(SERVICES)} services...")
    print("-" * 60)

    with ThreadPoolExecutor(max_workers=min(rps * 2, 20)) as pool:
        futures = []
        while time.monotonic() < deadline:
            # 30% of requests are intentional error paths
            force_error = random.random() < 0.30
            service_name = random.choice(list(SERVICES.keys()))
            cfg = SERVICES[service_name]

            futures.append(pool.submit(_hit, service_name, cfg, force_error))
            time.sleep(interval)

        for fut in as_completed(futures):
            r = fut.result()
            results.append(r)
            total += 1
            if r.status == 0:
                unreachable.add(r.service)
            elif r.is_error:
                errors += 1

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print(f"  TRAFFIC SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Duration:      {duration_s}s")
    print(f"  Total requests:{total:>6}")
    print(f"  Errors (5xx):  {errors:>6}  ({errors/max(total,1)*100:.0f}%)")

    if unreachable:
        print(f"\n  ! Unreachable services (not running?): {', '.join(unreachable)}")

    print(f"\n  By service:")
    from collections import Counter
    svc_counts = Counter(r.service for r in results)
    svc_errors = Counter(r.service for r in results if r.is_error and r.status != 0)
    avg_latency = {s: sum(r.latency_ms for r in results if r.service == s) / max(svc_counts[s], 1)
                   for s in SERVICES}

    for svc, count in sorted(svc_counts.items()):
        e = svc_errors.get(svc, 0)
        print(f"    {svc:<22} {count:>4} reqs  {e:>3} errors  "
              f"{avg_latency[svc]:>5.0f}ms avg")

    print(f"\n  Generated {errors} errors across {len(SERVICES)} services.")
    print(f"  Check your dashboard: http://localhost:3002\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incident reporter traffic generator")
    parser.add_argument("--duration", type=int, default=60, help="seconds to run (default: 60)")
    parser.add_argument("--rps", type=int, default=5, help="requests per second (default: 5)")
    args = parser.parse_args()

    try:
        run(args.duration, args.rps)
    except KeyboardInterrupt:
        print("\nStopped.")
