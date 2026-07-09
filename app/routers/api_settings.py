from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import SettingsUpdate, Status
from app import storage
from app.xray_runtime import service_status, xray_config_path

router = APIRouter(prefix="/api")


@router.get("/settings")
def get_settings():
    return storage.load_settings()


@router.post("/settings")
def update_settings(payload: SettingsUpdate):
    try:
        return storage.update_settings(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status", response_model=Status)
def get_status():
    settings = storage.load_settings()
    status = service_status(settings)
    service_active = status.stdout.strip() or status.stderr.strip() or "unknown"
    return Status(
        xray_path=settings.xray_path,
        xray_config=str(xray_config_path(settings)),
        xray_service_name=settings.xray_service_name,
        tunnel_count=len(settings.tunnels),
        enabled_tunnel_count=len([item for item in settings.tunnels if item.enable]),
        service_active=service_active,
    )
