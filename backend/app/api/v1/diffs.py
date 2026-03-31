import uuid
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.mongodb import get_mongo_db, normalize_mongo_id
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.diff import DiffDetail, DiffRead
from app.services.monitor_service import get_monitor
from app.utils.pagination import PaginationParams

router = APIRouter(tags=["diffs"])


@router.get("/monitors/{monitor_id}/diffs", response_model=dict)
async def list_diffs(
    monitor_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    has_changes: bool | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    monitor = await get_monitor(db, monitor_id, user.id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")

    mongo_db = get_mongo_db()
    collection = mongo_db.diffs

    query_filter: dict[str, Any] = {"monitor_id": str(monitor_id)}
    if has_changes is not None:
        query_filter["is_empty_after_filter"] = not has_changes

    total = await collection.count_documents(query_filter)
    cursor = (
        collection.find(query_filter, {"unified_diff": 0, "filtered_diff": 0})
        .sort("created_at", -1)
        .skip(pagination.offset)
        .limit(pagination.per_page)
    )

    items = []
    async for doc in cursor:
        normalize_mongo_id(doc)
        items.append(DiffRead(**doc))

    return pagination.paginate(items, total)


@router.get("/diffs/{diff_id}", response_model=DiffDetail)
async def get_diff(
    diff_id: str,
    user: User = Depends(get_current_user),
) -> DiffDetail:
    mongo_db = get_mongo_db()
    try:
        oid = ObjectId(diff_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid diff ID")

    doc = await mongo_db.diffs.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diff not found")

    doc["id"] = str(doc.pop("_id"))
    return DiffDetail(**doc)
