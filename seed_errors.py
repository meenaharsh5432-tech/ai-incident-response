"""
Seed script — sends realistic errors to test clustering + AI diagnosis.
Usage: python seed_errors.py [--url http://localhost:8001] [--repeat N]
"""
import argparse
import json
import random
import time
import urllib.request
import urllib.error

ERRORS = [
    # ── Database ──────────────────────────────────────────────────────────────
    {
        "error_type": "DatabaseConnectionError",
        "message": "could not obtain connection from the pool after 30s",
        "stack_trace": (
            "sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached,\n"
            "  connection timed out, timeout 30\n"
            "  File 'app/db.py', line 42, in get_connection\n"
            "  File 'app/models/user.py', line 118, in find_by_id"
        ),
        "service_name": "user-service",
        "environment": "prod",
        "metadata": {"cpu": 82, "memory_mb": 1200},
    },
    {
        "error_type": "DatabaseConnectionError",
        "message": "connection pool exhausted — no available connections",
        "stack_trace": (
            "psycopg2.OperationalError: FATAL: remaining connection slots are reserved\n"
            "  File 'app/db.py', line 38, in acquire\n"
            "  File 'app/routes/profile.py', line 55, in get_profile"
        ),
        "service_name": "user-service",
        "environment": "prod",
    },
    {
        "error_type": "DatabaseDeadlock",
        "message": "deadlock detected while updating orders table",
        "stack_trace": (
            "psycopg2.errors.DeadlockDetected: deadlock detected\n"
            "DETAIL: Process 1234 waits for ShareLock on transaction 5678;\n"
            "blocked by process 9012.\n"
            "  File 'app/services/order.py', line 201, in update_status\n"
            "  File 'app/workers/fulfillment.py', line 88, in process_batch"
        ),
        "service_name": "order-service",
        "environment": "prod",
        "metadata": {"table": "orders", "rows_locked": 150},
    },
    {
        "error_type": "SlowQueryTimeout",
        "message": "query exceeded 30s timeout: SELECT * FROM analytics_events",
        "stack_trace": (
            "django.db.utils.OperationalError: canceling statement due to statement timeout\n"
            "  File 'analytics/views.py', line 77, in get_events\n"
            "  File 'analytics/queries.py', line 33, in fetch_raw"
        ),
        "service_name": "analytics-service",
        "environment": "prod",
        "metadata": {"query_time_ms": 31200, "table": "analytics_events", "rows": 2000000},
    },
    {
        "error_type": "MigrationError",
        "message": "column 'user_id' of relation 'sessions' already exists",
        "stack_trace": (
            "psycopg2.errors.DuplicateColumn: column 'user_id' of relation 'sessions' already exists\n"
            "  File 'alembic/versions/0042_add_user_id.py', line 18, in upgrade\n"
            "  File 'alembic/env.py', line 91, in run_migrations"
        ),
        "service_name": "auth-service",
        "environment": "staging",
    },

    # ── Memory & Resources ────────────────────────────────────────────────────
    {
        "error_type": "OutOfMemoryError",
        "message": "Java heap space exhausted",
        "stack_trace": (
            "java.lang.OutOfMemoryError: Java heap space\n"
            "\tat java.util.Arrays.copyOf(Arrays.java:3210)\n"
            "\tat com.example.ReportGenerator.buildReport(ReportGenerator.java:244)\n"
            "\tat com.example.ReportController.generate(ReportController.java:89)"
        ),
        "service_name": "reporting-service",
        "environment": "prod",
        "metadata": {"heap_used_mb": 2048, "heap_max_mb": 2048},
    },
    {
        "error_type": "MemoryLeakDetected",
        "message": "RSS memory grew from 200MB to 1.8GB over 6 hours without GC relief",
        "stack_trace": (
            "Error: process.memoryUsage().rss exceeded threshold\n"
            "    at MemoryMonitor.check (monitor.js:45)\n"
            "    at Timeout._onTimeout (monitor.js:12)\n"
            "    at listOnTimeout (node:internal/timers:559:17)"
        ),
        "service_name": "notification-service",
        "environment": "prod",
        "metadata": {"rss_mb": 1843, "heap_used_mb": 1200, "uptime_hours": 6},
    },
    {
        "error_type": "DiskSpaceFull",
        "message": "no space left on device while writing to /var/log/app",
        "stack_trace": (
            "OSError: [Errno 28] No space left on device: '/var/log/app/access.log'\n"
            "  File 'logging/handlers.py', line 118, in emit\n"
            "  File 'app/middleware/logger.py', line 44, in log_request"
        ),
        "service_name": "api-gateway",
        "environment": "prod",
        "metadata": {"disk_used_percent": 100, "path": "/var/log/app"},
    },
    {
        "error_type": "CPUThrottling",
        "message": "container CPU throttled: 94% throttle ratio over last 5 minutes",
        "stack_trace": (
            "WARNING: CPU throttling detected by cgroup controller\n"
            "  cpu.stat: nr_throttled=1420 throttled_time=28400000000\n"
            "  Affected workload: image-resize worker pool"
        ),
        "service_name": "media-service",
        "environment": "prod",
        "metadata": {"cpu_throttle_pct": 94, "cpu_limit_cores": 0.5},
    },

    # ── Authentication & Security ─────────────────────────────────────────────
    {
        "error_type": "AuthenticationError",
        "message": "JWT signature verification failed: token has been tampered",
        "stack_trace": (
            "jose.exceptions.JWTError: Signature verification failed\n"
            "  File 'middleware/auth.py', line 29, in verify_token\n"
            "  File 'routes/api.py', line 12, in protected_route"
        ),
        "service_name": "api-gateway",
        "environment": "prod",
    },
    {
        "error_type": "BruteForceDetected",
        "message": "10 failed login attempts from IP 203.0.113.42 within 60 seconds",
        "stack_trace": (
            "SecurityError: rate limit exceeded for login endpoint\n"
            "  File 'auth/rate_limiter.py', line 67, in check_login_rate\n"
            "  File 'auth/views.py', line 33, in login"
        ),
        "service_name": "auth-service",
        "environment": "prod",
        "metadata": {"ip": "203.0.113.42", "attempts": 10, "window_seconds": 60},
    },
    {
        "error_type": "OAuthTokenExpired",
        "message": "refresh token has expired or been revoked",
        "stack_trace": (
            "requests_oauthlib.TokenExpiredError: (token_expired) Token has expired\n"
            "  File 'integrations/google.py', line 55, in refresh_credentials\n"
            "  File 'tasks/calendar_sync.py', line 22, in sync_user_calendar"
        ),
        "service_name": "integration-service",
        "environment": "prod",
    },
    {
        "error_type": "SSLCertificateExpired",
        "message": "SSL certificate for payments.internal expired 2 days ago",
        "stack_trace": (
            "ssl.SSLCertVerificationError: certificate verify failed: certificate has expired\n"
            "  File 'httpx/_transports/default.py', line 66, in handle_request\n"
            "  File 'services/payment_client.py', line 41, in post"
        ),
        "service_name": "billing-service",
        "environment": "prod",
        "metadata": {"host": "payments.internal", "expired_days_ago": 2},
    },

    # ── Network & Integrations ────────────────────────────────────────────────
    {
        "error_type": "RateLimitExceeded",
        "message": "429 Too Many Requests from upstream payment provider",
        "stack_trace": (
            "httpx.HTTPStatusError: 429 Too Many Requests\n"
            "  File 'services/payment.py', line 78, in charge_card\n"
            "  File 'workers/billing.py', line 34, in process_invoice"
        ),
        "service_name": "billing-service",
        "environment": "prod",
        "metadata": {"retry_after": 60, "provider": "stripe"},
    },
    {
        "error_type": "ServiceUnavailable",
        "message": "upstream inventory-service returned 503 after 3 retries",
        "stack_trace": (
            "aiohttp.ClientResponseError: 503 Service Unavailable\n"
            "  File 'clients/inventory.py', line 88, in get_stock\n"
            "  File 'services/checkout.py', line 134, in validate_cart"
        ),
        "service_name": "order-service",
        "environment": "prod",
        "metadata": {"upstream": "inventory-service", "retries": 3},
    },
    {
        "error_type": "ConnectionTimeout",
        "message": "connection to Redis timed out after 5000ms",
        "stack_trace": (
            "redis.exceptions.ConnectionError: Error 110 connecting to redis:6379. Connection timed out.\n"
            "  File 'cache/client.py', line 29, in get\n"
            "  File 'app/middleware/cache.py', line 55, in get_cached_response"
        ),
        "service_name": "api-gateway",
        "environment": "prod",
        "metadata": {"host": "redis", "port": 6379, "timeout_ms": 5000},
    },
    {
        "error_type": "DNSResolutionFailed",
        "message": "failed to resolve hostname 'email-provider.internal'",
        "stack_trace": (
            "socket.gaierror: [Errno -2] Name or service not known\n"
            "  File 'notifications/email.py', line 33, in send\n"
            "  File 'workers/notification_worker.py', line 77, in dispatch"
        ),
        "service_name": "notification-service",
        "environment": "prod",
        "metadata": {"hostname": "email-provider.internal"},
    },
    {
        "error_type": "WebhookDeliveryFailed",
        "message": "webhook to https://customer.example.com/hooks failed after 5 attempts",
        "stack_trace": (
            "MaxRetriesExceededError: webhook delivery failed\n"
            "  attempts: 5, last_status: 500\n"
            "  File 'webhooks/dispatcher.py', line 102, in deliver\n"
            "  File 'webhooks/scheduler.py', line 44, in process_queue"
        ),
        "service_name": "integration-service",
        "environment": "prod",
        "metadata": {"endpoint": "https://customer.example.com/hooks", "attempts": 5},
    },

    # ── Application Logic ─────────────────────────────────────────────────────
    {
        "error_type": "NullPointerException",
        "message": "Cannot read property 'id' of undefined",
        "stack_trace": (
            "TypeError: Cannot read properties of undefined (reading 'id')\n"
            "  at OrderService.processOrder (order.service.ts:67)\n"
            "  at async OrderController.create (order.controller.ts:34)"
        ),
        "service_name": "order-service",
        "environment": "prod",
    },
    {
        "error_type": "ValidationError",
        "message": "request body failed schema validation: 'email' is not a valid email address",
        "stack_trace": (
            "pydantic.ValidationError: 1 validation error for UserCreate\n"
            "email\n"
            "  value is not a valid email address (type=value_error.email)\n"
            "  File 'routers/users.py', line 44, in create_user"
        ),
        "service_name": "user-service",
        "environment": "prod",
        "metadata": {"field": "email", "value": "not-an-email"},
    },
    {
        "error_type": "DataCorruption",
        "message": "checksum mismatch for uploaded file: expected abc123 got def456",
        "stack_trace": (
            "IntegrityError: checksum verification failed\n"
            "  expected: abc123def456\n"
            "  actual:   def456abc123\n"
            "  File 'storage/s3.py', line 88, in upload_file\n"
            "  File 'api/media.py', line 55, in upload"
        ),
        "service_name": "media-service",
        "environment": "prod",
        "metadata": {"file_size_mb": 42, "bucket": "user-uploads"},
    },
    {
        "error_type": "RaceCondition",
        "message": "duplicate key value violates unique constraint 'orders_reference_key'",
        "stack_trace": (
            "sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation)\n"
            "DETAIL: Key (reference)=(ORD-20240101-9999) already exists.\n"
            "  File 'services/order.py', line 78, in create_order\n"
            "  File 'api/checkout.py', line 33, in place_order"
        ),
        "service_name": "order-service",
        "environment": "prod",
    },
    {
        "error_type": "InfiniteLoop",
        "message": "maximum recursion depth exceeded in category tree traversal",
        "stack_trace": (
            "RecursionError: maximum recursion depth exceeded\n"
            "  File 'models/category.py', line 55, in get_children\n"
            "  File 'models/category.py', line 55, in get_children\n"
            "  File 'models/category.py', line 55, in get_children\n"
            "  [Previous line repeated 996 more times]"
        ),
        "service_name": "catalog-service",
        "environment": "prod",
    },

    # ── Infrastructure & Deployment ───────────────────────────────────────────
    {
        "error_type": "KubernetesOOMKilled",
        "message": "container killed by OOMKiller: exceeded memory limit of 512Mi",
        "stack_trace": (
            "Exit code: 137 (OOMKilled)\n"
            "Reason: OOMKilled\n"
            "Last State: terminated\n"
            "  Container: search-worker\n"
            "  Memory limit: 512Mi\n"
            "  Memory usage at kill: 514Mi"
        ),
        "service_name": "search-service",
        "environment": "prod",
        "metadata": {"memory_limit_mi": 512, "memory_used_mi": 514, "pod": "search-worker-7d9f"},
    },
    {
        "error_type": "ConfigMapMissing",
        "message": "environment variable DATABASE_URL not set — missing ConfigMap binding",
        "stack_trace": (
            "KeyError: 'DATABASE_URL'\n"
            "  File 'app/config.py', line 12, in get_settings\n"
            "  File 'app/main.py', line 8, in create_app"
        ),
        "service_name": "payment-service",
        "environment": "staging",
    },
    {
        "error_type": "HealthCheckFailed",
        "message": "liveness probe failed: HTTP probe failed with statuscode: 503",
        "stack_trace": (
            "Warning: Liveness probe failed: HTTP probe failed with statuscode: 503\n"
            "Warning: Unhealthy: Readiness probe failed\n"
            "  GET /health → 503 Service Unavailable\n"
            "  Restarting container recommendation-api (attempt 3)"
        ),
        "service_name": "recommendation-service",
        "environment": "prod",
        "metadata": {"restart_count": 3, "probe_path": "/health"},
    },
    {
        "error_type": "CronJobFailed",
        "message": "nightly report generation cron job failed: exit code 1",
        "stack_trace": (
            "CronJob reports/nightly-summary failed\n"
            "Exit code: 1\n"
            "  File 'jobs/report.py', line 144, in generate_summary\n"
            "  File 'jobs/report.py', line 88, in fetch_data\n"
            "OperationalError: server closed the connection unexpectedly"
        ),
        "service_name": "reporting-service",
        "environment": "prod",
        "metadata": {"job": "nightly-summary", "duration_seconds": 3601},
    },

    # ── Message Queue & Async ─────────────────────────────────────────────────
    {
        "error_type": "MessageQueueFull",
        "message": "Kafka consumer lag exceeded threshold: 500,000 messages behind",
        "stack_trace": (
            "ConsumerLagAlert: topic=order-events partition=3 lag=512000\n"
            "  Consumer group: order-processor\n"
            "  Last committed offset: 1000000\n"
            "  Log end offset: 1512000"
        ),
        "service_name": "order-service",
        "environment": "prod",
        "metadata": {"topic": "order-events", "lag": 512000, "consumer_group": "order-processor"},
    },
    {
        "error_type": "DeadLetterQueueFull",
        "message": "DLQ for payment-events has 10,000 unprocessed messages",
        "stack_trace": (
            "AlertManager: dead_letter_queue_size{queue='payment-events-dlq'} > 10000\n"
            "  Messages failing since: 2024-01-15T03:22:00Z\n"
            "  Common error: SerializationException: Unknown magic byte"
        ),
        "service_name": "billing-service",
        "environment": "prod",
        "metadata": {"queue": "payment-events-dlq", "size": 10000},
    },
    {
        "error_type": "AsyncTaskTimeout",
        "message": "celery task send_welcome_email timed out after 300s",
        "stack_trace": (
            "celery.exceptions.SoftTimeLimitExceeded\n"
            "  Task: notifications.tasks.send_welcome_email\n"
            "  Task ID: 7f3d9a1c-4b2e-11ef-9c21-0242ac120002\n"
            "  File 'notifications/tasks.py', line 44, in send_welcome_email\n"
            "  File 'notifications/email.py', line 88, in render_template"
        ),
        "service_name": "notification-service",
        "environment": "prod",
        "metadata": {"task": "send_welcome_email", "timeout_seconds": 300},
    },

    # ── Third-party & External ────────────────────────────────────────────────
    {
        "error_type": "PaymentDeclined",
        "message": "Stripe charge failed: card_declined — insufficient_funds",
        "stack_trace": (
            "stripe.error.CardError: Your card has insufficient funds.\n"
            "  Code: card_declined\n"
            "  Decline code: insufficient_funds\n"
            "  File 'payments/stripe_client.py', line 67, in charge\n"
            "  File 'api/checkout.py', line 102, in complete_purchase"
        ),
        "service_name": "billing-service",
        "environment": "prod",
        "metadata": {"decline_code": "insufficient_funds", "amount_cents": 9999},
    },
    {
        "error_type": "S3AccessDenied",
        "message": "AccessDenied: s3:PutObject on arn:aws:s3:::user-uploads/avatars/",
        "stack_trace": (
            "botocore.exceptions.ClientError: An error occurred (AccessDenied)\n"
            "  when calling the PutObject operation:\n"
            "  Access Denied\n"
            "  File 'storage/s3.py', line 55, in upload\n"
            "  File 'api/profile.py', line 33, in update_avatar"
        ),
        "service_name": "media-service",
        "environment": "prod",
        "metadata": {"bucket": "user-uploads", "key": "avatars/"},
    },
    {
        "error_type": "ElasticsearchIndexError",
        "message": "index product-catalog-v2 is read-only: disk watermark exceeded",
        "stack_trace": (
            "elasticsearch.exceptions.AuthorizationException: [403]\n"
            "  blocked by: [FORBIDDEN/12/index read-only / allow delete (api)];\n"
            "  [type=cluster_block_exception]\n"
            "  File 'search/indexer.py', line 78, in index_product\n"
            "  File 'workers/catalog_sync.py', line 44, in sync"
        ),
        "service_name": "search-service",
        "environment": "prod",
        "metadata": {"index": "product-catalog-v2", "disk_usage_pct": 95},
    },
]


def post_error(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{url}/api/errors",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8001")
    parser.add_argument("--repeat", type=int, default=1, help="Send each error N times")
    parser.add_argument("--delay", type=float, default=0.3, help="Seconds between requests")
    parser.add_argument("--shuffle", action="store_true", help="Randomise order")
    args = parser.parse_args()

    errors = list(ERRORS)
    if args.shuffle:
        random.shuffle(errors)

    print(f"Seeding {len(errors)} error types × {args.repeat} repeat(s) → {args.url}\n")

    new_count = clustered_count = fail_count = 0

    for _ in range(args.repeat):
        for err in errors:
            try:
                result = post_error(args.url, err)
                if result["is_new_incident"]:
                    new_count += 1
                    tag = "NEW      "
                else:
                    clustered_count += 1
                    tag = "clustered"
                print(f"[{tag}] incident={result['incident_id']}  {err['error_type']} @ {err['service_name']}")
            except urllib.error.HTTPError as e:
                fail_count += 1
                print(f"  HTTP {e.code}: {err['error_type']}")
            except Exception as e:
                fail_count += 1
                print(f"  ERROR: {e}")
            time.sleep(args.delay + random.uniform(0, 0.05))

    print(f"\n{'─'*55}")
    print(f"  New incidents : {new_count}")
    print(f"  Clustered     : {clustered_count}")
    print(f"  Errors        : {fail_count}")
    print(f"\nDashboard → http://localhost:3002")


if __name__ == "__main__":
    main()
