from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import storage
from app.models import Tunnel
from app.xray_config import build_a_side_text
from app.xray_runtime import apply_config

router = APIRouter(prefix="/api/tunnels")


def apply_saved_change(tunnel: Tunnel | None = None) -> dict:
    result = apply_config(storage.load_settings())
    return {
        "saved": True,
        "applied": result.ok,
        "tunnel": tunnel,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@router.get("")
def list_tunnels():
    return storage.list_tunnels()


@router.post("")
def create_tunnel(payload: Tunnel):
    try:
        tunnel = storage.add_tunnel(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return apply_saved_change(tunnel)


@router.put("/{tunnel_id}")
def update_tunnel(tunnel_id: str, payload: Tunnel):
    try:
        tunnel = storage.update_tunnel(tunnel_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return apply_saved_change(tunnel)


@router.delete("/{tunnel_id}")
def delete_tunnel(tunnel_id: str):
    try:
        storage.delete_tunnel(tunnel_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return apply_saved_change()


@router.post("/{tunnel_id}/toggle")
def toggle_tunnel(tunnel_id: str):
    try:
        tunnel = storage.toggle_tunnel(tunnel_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return apply_saved_change(tunnel)


@router.post("/{tunnel_id}/copy-a-side")
def copy_a_side(tunnel_id: str):
    try:
        settings = storage.load_settings()
        tunnel = storage.get_tunnel(tunnel_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"text": build_a_side_text(settings, tunnel)}
