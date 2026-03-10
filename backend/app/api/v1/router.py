from fastapi import APIRouter

from app.api.v1 import admin, alerts, auth, diffs, monitors, notifications, snapshots, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(monitors.router)
api_router.include_router(alerts.router)
api_router.include_router(snapshots.router)
api_router.include_router(diffs.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
