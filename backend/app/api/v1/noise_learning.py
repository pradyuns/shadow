import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.mongodb import get_mongo_db
from app.db.postgres import get_db
from app.models.monitor import Monitor
from app.models.user import User
from app.schemas.noise_learning import (
    LearnedNoisePatternRead,
    MonitorNoiseLearningRead,
    NoiseLearningOverviewItem,
)
from app.services.monitor_service import get_monitor
from app.utils.pagination import PaginationParams
from workers.scraper.adaptive_noise_learning import (
    LEARNED_PATTERNS_COLLECTION,
    sum_recent_filter_events,
    summarize_monitor_patterns,
)

router = APIRouter(tags=["noise-learning"])


@router.get("/monitors/{monitor_id}/noise-learning", response_model=MonitorNoiseLearningRead)
async def get_monitor_noise_learning(
    monitor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MonitorNoiseLearningRead:
    monitor = await get_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    mongo_db = get_mongo_db()
    collection = mongo_db[LEARNED_PATTERNS_COLLECTION]

    docs = [doc async for doc in collection.find({"monitor_id": str(monitor_id)}).sort("confidence", -1)]
    now = datetime.now(timezone.utc)
    summary = summarize_monitor_patterns(docs, now=now)

    patterns = []
    for doc in docs:
        stats = doc.get("stats", {})
        patterns.append(
            LearnedNoisePatternRead(
                id=str(doc.get("_id")),
                pattern=doc.get("pattern", ""),
                template=doc.get("template", ""),
                support_count=int(doc.get("support_count", 0)),
                confidence=round(float(doc.get("confidence", 0.0)), 3),
                decay_score=round(float(doc.get("decay_score", 0.0)), 3),
                is_active=bool(doc.get("is_active", False)),
                manual_review_required=bool(doc.get("manual_review_required", False)),
                blocked_reason=doc.get("blocked_reason"),
                lines_filtered_7d=sum_recent_filter_events(stats.get("recent_filter_events", []), now, days=7),
                total_lines_filtered=int(stats.get("total_lines_filtered", 0)),
                first_seen_at=doc.get("first_seen_at"),
                last_seen_at=doc.get("last_seen_at"),
                last_matched_at=doc.get("last_matched_at"),
                examples=doc.get("examples", []),
            )
        )

    return MonitorNoiseLearningRead(
        monitor_id=str(monitor.id),
        monitor_name=monitor.name,
        learned_patterns=int(summary["learned_patterns"]),
        active_patterns=int(summary["active_patterns"]),
        manual_review_patterns=int(summary["manual_review_patterns"]),
        lines_filtered_7d=int(summary["lines_filtered_7d"]),
        total_lines_filtered=int(summary["total_lines_filtered"]),
        avg_confidence=float(summary["avg_confidence"]),
        patterns=patterns,
    )


@router.get("/noise-learning/overview", response_model=dict)
async def get_noise_learning_overview(
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Monitor.id, Monitor.name, Monitor.competitor_name).where(
            Monitor.user_id == user.id,
            Monitor.deleted_at.is_(None),
        )
    )
    monitor_rows = list(result.all())
    if not monitor_rows:
        return pagination.paginate([], 0)

    monitor_ids = [str(row.id) for row in monitor_rows]
    monitor_lookup = {str(row.id): {"name": row.name, "competitor_name": row.competitor_name} for row in monitor_rows}

    mongo_db = get_mongo_db()
    collection = mongo_db[LEARNED_PATTERNS_COLLECTION]

    grouped: dict[str, list[dict[str, Any]]] = {monitor_id: [] for monitor_id in monitor_ids}
    async for doc in collection.find(
        {"monitor_id": {"$in": monitor_ids}},
        {"monitor_id": 1, "is_active": 1, "manual_review_required": 1, "confidence": 1, "stats": 1},
    ):
        monitor_id = doc.get("monitor_id")
        if isinstance(monitor_id, str):
            grouped.setdefault(monitor_id, []).append(doc)

    now = datetime.now(timezone.utc)
    items: list[NoiseLearningOverviewItem] = []
    for monitor_id in monitor_ids:
        docs = grouped.get(monitor_id, [])
        if not docs:
            continue
        summary = summarize_monitor_patterns(docs, now=now)
        lookup = monitor_lookup[monitor_id]
        items.append(
            NoiseLearningOverviewItem(
                monitor_id=monitor_id,
                monitor_name=lookup["name"],
                competitor_name=lookup["competitor_name"],
                learned_patterns=int(summary["learned_patterns"]),
                active_patterns=int(summary["active_patterns"]),
                manual_review_patterns=int(summary["manual_review_patterns"]),
                lines_filtered_7d=int(summary["lines_filtered_7d"]),
                avg_confidence=float(summary["avg_confidence"]),
            )
        )

    items.sort(
        key=lambda item: (
            item.lines_filtered_7d,
            item.learned_patterns,
            item.avg_confidence,
        ),
        reverse=True,
    )

    total = len(items)
    start = pagination.offset
    end = start + pagination.per_page
    return pagination.paginate(items[start:end], total)
