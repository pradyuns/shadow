"""Prometheus metrics for the Competitor Intelligence Monitor.

Metrics are collected in-process and exposed at /metrics.
"""

from prometheus_client import Counter, Histogram, Info

# App info
app_info = Info("app", "Application information")
app_info.info({"name": "competitor_monitor", "version": "0.1.0"})

# API request metrics
api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    labelnames=["method", "path", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Scraping metrics
scrape_duration = Histogram(
    "scrape_duration_seconds",
    "Time to scrape a single URL",
    labelnames=["render_method"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

scrape_success_total = Counter(
    "scrape_success_total",
    "Total successful scrapes",
    labelnames=["render_method"],
)

scrape_failure_total = Counter(
    "scrape_failure_total",
    "Total failed scrapes",
    labelnames=["render_method", "error_type"],
)

# Claude API metrics
claude_api_duration = Histogram(
    "claude_api_duration_seconds",
    "Claude API call duration",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

claude_api_cost_usd = Counter(
    "claude_api_cost_usd_total",
    "Total Claude API cost in USD",
)

claude_api_tokens = Counter(
    "claude_api_tokens_total",
    "Total Claude API tokens used",
    labelnames=["type"],  # prompt, completion
)

# Notification metrics
notification_sent_total = Counter(
    "notification_sent_total",
    "Total notifications sent",
    labelnames=["channel", "status"],  # channel: slack/email, status: success/failure
)

# Alert metrics
alert_created_total = Counter(
    "alert_created_total",
    "Total alerts created",
    labelnames=["severity"],
)

alert_suppressed_total = Counter(
    "alert_suppressed_total",
    "Total alerts suppressed",
    labelnames=["reason"],
)
