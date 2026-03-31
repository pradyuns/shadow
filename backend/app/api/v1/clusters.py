import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_verified_user
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.alert import ClusterDetail, ClusterRead
from app.services.alert_service import get_cluster, list_clusters, resolve_cluster
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=dict)
async def list_all(
    pagination: PaginationParams = Depends(),
    is_resolved: bool | None = None,
    competitor_name: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    clusters, total = await list_clusters(
        db,
        user.id,
        pagination.page,
        pagination.per_page,
        is_resolved=is_resolved,
        competitor_name=competitor_name,
    )
    return pagination.paginate(
        [ClusterRead.model_validate(c) for c in clusters],
        total,
    )


@router.get("/{cluster_id}", response_model=ClusterDetail)
async def get_one(
    cluster_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClusterDetail:
    cluster = await get_cluster(db, cluster_id, user.id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")
    return ClusterDetail.model_validate(cluster)


@router.patch("/{cluster_id}/resolve", response_model=ClusterDetail)
async def resolve(
    cluster_id: uuid.UUID,
    user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> ClusterDetail:
    cluster = await get_cluster(db, cluster_id, user.id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")
    cluster = await resolve_cluster(db, cluster)
    return ClusterDetail.model_validate(cluster)
