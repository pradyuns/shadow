import uuid
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.mongodb import get_mongo_db, normalize_mongo_id
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.snapshot import SnapshotDetail, SnapshotRead
from app.services.monitor_service import get_monitor
from app.utils.pagination import PaginationParams

router = APIRouter(tags=["snapshots"])


@router.get("/monitors/{monitor_id}/snapshots", response_model=dict)
async def list_snapshots(
    monitor_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    monitor = await get_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    mongo_db = get_mongo_db()
    collection = mongo_db.snapshots

    total = await collection.count_documents({"monitor_id": str(monitor_id)})
    cursor = (
        collection.find({"monitor_id": str(monitor_id)}, {"raw_html": 0, "extracted_text": 0})
        .sort("created_at", -1)
        .skip(pagination.offset)
        .limit(pagination.per_page)
    )

    items = []
    async for doc in cursor:
        normalize_mongo_id(doc)
        items.append(SnapshotRead(**doc))

    return pagination.paginate(items, total)


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotDetail)
async def get_snapshot(
    snapshot_id: str,
    include_html: bool = Query(default=False),
    user: User = Depends(get_current_user),
) -> SnapshotDetail:
    mongo_db = get_mongo_db()
    try:
        oid = ObjectId(snapshot_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid snapshot ID")

    projection = None if include_html else {"raw_html": 0}
    doc = await mongo_db.snapshots.find_one({"_id": oid}, projection)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    doc["id"] = str(doc.pop("_id"))
    if not include_html:
        doc["raw_html"] = None
    return SnapshotDetail(**doc)
