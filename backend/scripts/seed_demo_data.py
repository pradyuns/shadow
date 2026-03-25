"""Seed realistic demo data for landing page metrics.

Run: docker compose exec api python -m scripts.seed_demo_data

What it creates (from real-world-like scenarios):
- 14 monitors across 5 competitors watching pricing, changelogs, docs, features, hiring
- ~240 snapshots (roughly 17 per monitor over simulated weeks)
- ~110 diffs with realistic noise filtering stats
- 23 alerts at various severity levels

All numbers come from querying this seeded data — nothing is hardcoded on the frontend.
"""

import hashlib
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import Alert
from app.models.monitor import Monitor
from app.models.user import User
from workers.classifier.schemas import SEVERITY_ORDER

random.seed(42)  # Reproducible

# ── Competitors and pages to monitor ──────────────────────────────────────────
COMPETITORS = [
    {
        "name": "Acme Analytics",
        "pages": [
            ("Pricing", "https://acme-analytics.com/pricing", "pricing"),
            ("Changelog", "https://acme-analytics.com/changelog", "changelog"),
            ("Features", "https://acme-analytics.com/features", "feature_list"),
        ],
    },
    {
        "name": "Beacon AI",
        "pages": [
            ("Pricing", "https://beacon.ai/pricing", "pricing"),
            ("Docs", "https://docs.beacon.ai/api", "documentation"),
            ("Careers", "https://beacon.ai/careers", "hiring"),
        ],
    },
    {
        "name": "Cortex Platform",
        "pages": [
            ("Pricing", "https://cortexplatform.io/pricing", "pricing"),
            ("Changelog", "https://cortexplatform.io/changelog", "changelog"),
            ("Features", "https://cortexplatform.io/product", "feature_list"),
        ],
    },
    {
        "name": "DataForge",
        "pages": [
            ("Pricing", "https://dataforge.dev/pricing", "pricing"),
            ("API Docs", "https://dataforge.dev/docs/api", "documentation"),
        ],
    },
    {
        "name": "Elevate CRM",
        "pages": [
            ("Pricing", "https://elevatecrm.com/pricing", "pricing"),
            ("What's New", "https://elevatecrm.com/whats-new", "changelog"),
            ("Careers", "https://elevatecrm.com/jobs", "hiring"),
        ],
    },
]

# ── Realistic diff content templates ──────────────────────────────────────────
NOISE_EXAMPLES = [
    "+  © 2026 Acme Inc.",
    "+  csrf_token='a8f3b2c1d4'",
    "-  bundle.a1b2c3d4.js",
    "+  utm_source=google&utm_medium=cpc",
    "-  session_id='x9y8z7'",
    "+  nonce='randomvalue123'",
    "+  __cf_bm=abc123",
    "-  2026-03-10T14:22:31Z",
    "+  chunk-f4e5d6c7",
    "-  cookie_consent_v2",
]

REAL_CHANGE_EXAMPLES = {
    "pricing": [
        ("- Starter: $29/mo", "+ Starter: $39/mo"),
        ("- Free tier: 1,000 events", "+ Free tier: 500 events"),
        ("+ Enterprise: Custom pricing — contact sales"),
        ("- Annual discount: 20%", "+ Annual discount: 15%"),
    ],
    "changelog": [
        ("+ v3.2.0: Added bulk export for dashboards"),
        ("+ AI-powered anomaly detection now in beta"),
        ("- Deprecated: Legacy webhook format (removal Q3 2026)"),
        ("+ New: Role-based access control for teams"),
    ],
    "feature_list": [
        ("+ Real-time collaboration (up to 25 users)"),
        ("- Removed: On-premise deployment option"),
        ("+ Native Salesforce integration"),
        ("- Basic plan: 5 projects", "+ Basic plan: 3 projects"),
    ],
    "documentation": [
        ("+ POST /v2/batch — batch ingestion endpoint"),
        ("- Rate limit: 1000 req/min", "+ Rate limit: 500 req/min"),
        ("+ Authentication: OAuth 2.0 PKCE flow now supported"),
    ],
    "hiring": [
        ("+ Senior ML Engineer — Applied AI Team (New York)"),
        ("+ Staff Backend Engineer — Platform (Remote)"),
        ("- Removed: Frontend Engineer listing"),
    ],
}

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
SEVERITY_WEIGHTS = [0.05, 0.15, 0.35, 0.30, 0.15]


def make_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def build_unified_diff(page_type: str, include_noise: bool) -> tuple[str, int, int, int]:
    """Build a realistic unified diff. Returns (diff_text, lines_added, lines_removed, noise_lines)."""
    lines = ["--- a/page", "+++ b/page", "@@ -1,10 +1,12 @@"]
    added = 0
    removed = 0
    noise = 0

    # Add some context lines
    lines.append(" Some unchanged content on the page")
    lines.append(" Navigation bar and header area")

    # Real changes
    changes = REAL_CHANGE_EXAMPLES.get(page_type, REAL_CHANGE_EXAMPLES["changelog"])
    selected = random.sample(changes, min(random.randint(1, 3), len(changes)))
    for change in selected:
        if isinstance(change, tuple):
            lines.append(change[0])
            lines.append(change[1])
            added += 1
            removed += 1
        else:
            lines.append(change)
            if change.startswith("+"):
                added += 1
            else:
                removed += 1

    # Noise lines (sometimes)
    if include_noise:
        noise_count = random.randint(2, 6)
        noise_selection = random.sample(NOISE_EXAMPLES, min(noise_count, len(NOISE_EXAMPLES)))
        for nl in noise_selection:
            lines.append(nl)
            noise += 1

    lines.append(" Footer content")
    return "\n".join(lines), added, removed, noise


def seed():
    engine = create_engine(str(settings.database_url_sync))

    # MongoDB
    mongo_client = MongoClient(str(settings.mongodb_url))
    db_name = str(settings.mongodb_url).rsplit("/", 1)[-1].split("?")[0]
    mongo_db = mongo_client[db_name]

    with Session(engine) as db:
        # Check if demo data already exists
        existing = db.execute(
            text("SELECT COUNT(*) FROM monitors WHERE competitor_name = 'Acme Analytics'")
        ).scalar()
        if existing and existing > 0:
            print("Demo data already exists. Skipping seed.")
            return

        # Get or create a demo user
        demo_user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo@shadow.io'")
        ).fetchone()

        if not demo_user:
            user_id = str(uuid.uuid4())
            db.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, full_name, is_active, is_admin, is_email_verified, max_monitors, created_at, updated_at) "
                    "VALUES (:id, :email, :pw, :name, true, true, true, 50, :now, :now)"
                ),
                {
                    "id": user_id,
                    "email": "demo@shadow.io",
                    "pw": "$2b$12$dummyhashnotarealpassword000000000000000000000000",
                    "name": "Demo User",
                    "now": datetime.now(timezone.utc),
                },
            )
        else:
            user_id = str(demo_user[0])

        now = datetime.now(timezone.utc)
        monitor_ids = []

        # ── Create monitors ──────────────────────────────────────────────
        for comp in COMPETITORS:
            for page_name, url, page_type in comp["pages"]:
                monitor_id = str(uuid.uuid4())
                monitor_ids.append((monitor_id, comp["name"], page_type, url))

                check_interval = random.choice([4, 6, 8, 12, 24])
                last_checked = now - timedelta(hours=random.randint(1, check_interval))

                db.execute(
                    text(
                        "INSERT INTO monitors (id, user_id, url, name, competitor_name, page_type, "
                        "check_interval_hours, is_active, last_checked_at, last_scrape_status, "
                        "consecutive_failures, created_at, updated_at) "
                        "VALUES (:id, :uid, :url, :name, :comp, :pt, :ci, true, :lc, 'success', 0, :ca, :now)"
                    ),
                    {
                        "id": monitor_id,
                        "uid": user_id,
                        "url": url,
                        "name": f"{comp['name']} — {page_name}",
                        "comp": comp["name"],
                        "pt": page_type,
                        "ci": check_interval,
                        "lc": last_checked,
                        "ca": now - timedelta(days=random.randint(14, 30)),
                        "now": now,
                    },
                )

        db.commit()
        print(f"Created {len(monitor_ids)} monitors")

        # ── Create snapshots and diffs ───────────────────────────────────
        total_snapshots = 0
        total_diffs = 0
        total_noise_lines = 0
        total_changed_lines = 0

        alert_data = []
        diff_analysis_map = {}  # diff_id -> analysis_id (avoid duplicate analyses)

        for monitor_id, comp_name, page_type, url in monitor_ids:
            # Each monitor gets 15-20 snapshots over the past ~3 weeks
            num_snapshots = random.randint(15, 20)
            prev_text = f"Baseline content for {comp_name} {page_type} page"
            prev_snapshot_id = None

            for snap_idx in range(num_snapshots):
                snap_time = now - timedelta(
                    days=random.uniform(0, 21),
                    hours=random.uniform(0, 24),
                )
                text_content = f"{prev_text}\nRevision {snap_idx}"
                text_hash = make_text_hash(text_content)

                snapshot_doc = {
                    "monitor_id": monitor_id,
                    "url": url,
                    "http_status": 200,
                    "render_method": random.choice(["fetch", "firecrawl"]),
                    "text_hash": text_hash,
                    "fetch_duration_ms": random.randint(200, 1800),
                    "extracted_text": text_content,
                    "status": "scraped",
                    "is_baseline": snap_idx == 0,
                    "created_at": snap_time,
                }
                result = mongo_db.snapshots.insert_one(snapshot_doc)
                snapshot_id = str(result.inserted_id)
                total_snapshots += 1

                # Create diff for non-baseline snapshots (not all — some are no-change)
                if prev_snapshot_id and random.random() < 0.55:
                    has_noise = random.random() < 0.72  # 72% of diffs have some noise
                    diff_text, added, removed, noise = build_unified_diff(page_type, has_noise)

                    is_empty = random.random() < 0.15  # 15% are noise-only
                    if is_empty:
                        noise = added + removed + noise
                        added = 0
                        removed = 0

                    diff_doc = {
                        "monitor_id": monitor_id,
                        "snapshot_before_id": prev_snapshot_id,
                        "snapshot_after_id": snapshot_id,
                        "unified_diff": diff_text,
                        "filtered_diff": diff_text if not is_empty else None,
                        "diff_lines_added": added,
                        "diff_lines_removed": removed,
                        "diff_size_bytes": len(diff_text.encode()),
                        "noise_lines_removed": noise,
                        "is_empty_after_filter": is_empty,
                        "created_at": snap_time,
                    }
                    mongo_db.diffs.insert_one(diff_doc)
                    total_diffs += 1
                    total_noise_lines += noise
                    total_changed_lines += added + removed

                    # Create alert for meaningful diffs
                    if not is_empty and random.random() < 0.35:
                        severity = random.choices(SEVERITIES, SEVERITY_WEIGHTS)[0]
                        latest_diff = mongo_db.diffs.find_one(
                            {"monitor_id": monitor_id},
                            sort=[("created_at", -1)],
                        )
                        diff_oid = str(latest_diff["_id"])

                        # Reuse existing analysis or create new one (unique index on diff_id)
                        if diff_oid in diff_analysis_map:
                            analysis_oid = diff_analysis_map[diff_oid]
                        else:
                            analysis_doc = {
                                "diff_id": diff_oid,
                                "monitor_id": monitor_id,
                                "significance_level": severity,
                                "summary": f"Change detected on {comp_name} {page_type} page",
                                "categories": [page_type],
                                "claude_model": "claude-sonnet-4-20250514",
                                "prompt_tokens": random.randint(400, 1200),
                                "completion_tokens": random.randint(80, 300),
                                "total_cost_usd": round(random.uniform(0.002, 0.015), 4),
                                "needs_review": severity in ("CRITICAL", "HIGH"),
                                "created_at": snap_time,
                            }
                            analysis_result = mongo_db.analyses.insert_one(analysis_doc)
                            analysis_oid = str(analysis_result.inserted_id)
                            diff_analysis_map[diff_oid] = analysis_oid

                        alert_data.append({
                            "id": str(uuid.uuid4()),
                            "monitor_id": monitor_id,
                            "user_id": user_id,
                            "severity": severity,
                            "summary": f"Change detected on {comp_name} {page_type} page",
                            "diff_id": diff_oid,
                            "analysis_id": analysis_oid,
                            "is_acknowledged": random.random() < 0.6,
                            "created_at": snap_time,
                        })

                prev_snapshot_id = snapshot_id
                prev_text = text_content

        # ── Create alerts ────────────────────────────────────────────────
        for a in alert_data:
            ack_at = a["created_at"] + timedelta(minutes=random.randint(5, 120)) if a["is_acknowledged"] else None
            db.execute(
                text(
                    "INSERT INTO alerts (id, monitor_id, user_id, severity, summary, diff_id, analysis_id, "
                    "is_acknowledged, acknowledged_at, created_at) "
                    "VALUES (:id, :mid, :uid, :sev, :sum, :did, :aid, :ack, :ack_at, :ca)"
                ),
                {
                    "id": a["id"],
                    "mid": a["monitor_id"],
                    "uid": a["user_id"],
                    "sev": a["severity"],
                    "sum": a["summary"],
                    "did": a["diff_id"],
                    "aid": a["analysis_id"],
                    "ack": a["is_acknowledged"],
                    "ack_at": ack_at,
                    "ca": a["created_at"],
                },
            )
        db.commit()

        # ── Cluster alerts ──────────────────────────────────────────────
        # Group alerts by competitor, then run the clustering algorithm
        from workers.clustering.alert_clusterer import (
            MERGE_THRESHOLD,
            _extract_keywords,
            _generate_cluster_title,
            compute_similarity,
        )

        # Build a lookup: monitor_id -> competitor_name
        monitor_competitor = {mid: comp for mid, comp, _, _ in monitor_ids}

        # Sort alerts by time for realistic online clustering
        sorted_alerts = sorted(alert_data, key=lambda a: a["created_at"])
        clusters = []  # list of {id, competitor, categories, keywords, time, alert_ids, severity}
        cluster_count = 0

        for a in sorted_alerts:
            competitor = monitor_competitor.get(a["monitor_id"], "Unknown")
            a_categories = set(a.get("categories", []) or [])
            # Infer category from the monitor's page_type
            page_type = next(
                (pt for mid, _, pt, _ in monitor_ids if mid == a["monitor_id"]),
                "other",
            )
            if not a_categories:
                a_categories = {page_type}
            a_keywords = _extract_keywords(a["summary"])
            a_time = a["created_at"]

            best_cluster = None
            best_score = 0.0
            for cluster in clusters:
                if cluster["competitor"] != competitor or cluster.get("closed"):
                    continue
                scores = compute_similarity(
                    a_categories, a_keywords, a_time,
                    cluster["categories"], cluster["keywords"], cluster["time"],
                )
                if scores["combined"] > best_score:
                    best_score = scores["combined"]
                    best_cluster = cluster

            if best_cluster and best_score >= MERGE_THRESHOLD:
                best_cluster["alert_ids"].append(a["id"])
                best_cluster["categories"] |= a_categories
                best_cluster["keywords"] |= a_keywords
                best_cluster["time"] = a_time
                best_cluster["alert_count"] += 1
                if SEVERITY_ORDER.get(a["severity"], 0) > SEVERITY_ORDER.get(best_cluster["severity"], 0):
                    best_cluster["severity"] = a["severity"]
            else:
                cluster_id = str(uuid.uuid4())
                clusters.append({
                    "id": cluster_id,
                    "competitor": competitor,
                    "title": _generate_cluster_title(competitor, list(a_categories), a["summary"]),
                    "categories": a_categories,
                    "keywords": a_keywords,
                    "time": a_time,
                    "alert_ids": [a["id"]],
                    "alert_count": 1,
                    "severity": a["severity"],
                })
                cluster_count += 1

        # Write clusters to DB
        for c in clusters:
            db.execute(
                text(
                    "INSERT INTO alert_clusters (id, user_id, competitor_name, title, severity, "
                    "alert_count, categories, summary_keywords, is_resolved, created_at, updated_at) "
                    "VALUES (:id, :uid, :comp, :title, :sev, :cnt, :cats, :kws, false, :ca, :ca)"
                ),
                {
                    "id": c["id"],
                    "uid": user_id,
                    "comp": c["competitor"],
                    "title": c["title"],
                    "sev": c["severity"],
                    "cnt": c["alert_count"],
                    "cats": json.dumps(list(c["categories"])),
                    "kws": json.dumps(list(c["keywords"])),
                    "ca": c["time"],
                },
            )
            # Assign alerts to cluster
            for aid in c["alert_ids"]:
                db.execute(
                    text("UPDATE alerts SET cluster_id = :cid WHERE id = :aid"),
                    {"cid": c["id"], "aid": aid},
                )
        db.commit()

        # ── Report ───────────────────────────────────────────────────────
        raw_total = total_changed_lines + total_noise_lines
        noise_pct = round((total_noise_lines / raw_total) * 100) if raw_total > 0 else 0

        print(f"\n{'═' * 50}")
        print(f"  Seed complete")
        print(f"{'═' * 50}")
        print(f"  Pages monitored:     {len(monitor_ids)}")
        print(f"  Snapshots processed: {total_snapshots}")
        print(f"  Diffs computed:      {total_diffs}")
        print(f"  Changes detected:    {total_diffs - sum(1 for d in [] if d)}")
        print(f"  Alerts created:      {len(alert_data)}")
        print(f"  Noise lines removed: {total_noise_lines}")
        print(f"  Total changed lines: {total_changed_lines}")
        print(f"  Noise filtered:      {noise_pct}%")
        print(f"{'═' * 50}\n")


if __name__ == "__main__":
    seed()
