from __future__ import annotations

from fastapi import APIRouter

from app import storage
from app.xray_config import build_xray_config
from app.xray_runtime import apply_config, restart_service, save_config, validate_config

router = APIRouter(prefix="/api/xray")


@router.get("/config")
def get_config():
    return build_xray_config(storage.load_settings())


@router.post("/validate")
def validate():
    return validate_config(storage.load_settings())


@router.post("/save")
def save():
    return save_config(storage.load_settings())


@router.post("/restart")
def restart():
    return restart_service(storage.load_settings())


@router.post("/apply")
def apply():
    return apply_config(storage.load_settings())
