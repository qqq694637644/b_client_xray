from __future__ import annotations

import json
import os
from pathlib import Path

from app.compat import dump_model
from app.config import SETTINGS_FILE
from app.models import Settings, SettingsUpdate, Tunnel


def _settings_file() -> Path:
    return SETTINGS_FILE


def load_settings() -> Settings:
    path = _settings_file()
    if not path.exists():
        settings = Settings()
        save_settings(settings)
        return settings
    data = json.loads(path.read_text(encoding="utf-8"))
    return Settings(**data)


def save_settings(settings: Settings) -> None:
    path = _settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(dump_model(settings), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def update_settings(update: SettingsUpdate) -> Settings:
    settings = load_settings()
    settings.xray_path = update.xray_path.strip()
    settings.xray_service_name = update.xray_service_name.strip()
    settings.panel_host = update.panel_host.strip()
    settings.panel_port = update.panel_port
    settings.public_address = update.public_address.strip()
    settings = Settings(**dump_model(settings))
    save_settings(settings)
    return settings


def list_tunnels() -> list[Tunnel]:
    return load_settings().tunnels


def _ensure_unique_port(settings: Settings, tunnel: Tunnel, ignore_id: str | None = None) -> None:
    for item in settings.tunnels:
        if ignore_id is not None and item.id == ignore_id:
            continue
        if item.port == tunnel.port:
            raise ValueError(f"port {tunnel.port} already exists")


def add_tunnel(tunnel: Tunnel) -> Tunnel:
    settings = load_settings()
    _ensure_unique_port(settings, tunnel)
    settings.tunnels.append(tunnel)
    save_settings(settings)
    return tunnel


def update_tunnel(tunnel_id: str, tunnel: Tunnel) -> Tunnel:
    settings = load_settings()
    _ensure_unique_port(settings, tunnel, ignore_id=tunnel_id)
    for index, item in enumerate(settings.tunnels):
        if item.id == tunnel_id:
            tunnel.id = tunnel_id
            settings.tunnels[index] = tunnel
            save_settings(settings)
            return tunnel
    raise KeyError(f"tunnel not found: {tunnel_id}")


def delete_tunnel(tunnel_id: str) -> None:
    settings = load_settings()
    new_tunnels = [item for item in settings.tunnels if item.id != tunnel_id]
    if len(new_tunnels) == len(settings.tunnels):
        raise KeyError(f"tunnel not found: {tunnel_id}")
    settings.tunnels = new_tunnels
    save_settings(settings)


def toggle_tunnel(tunnel_id: str) -> Tunnel:
    settings = load_settings()
    for item in settings.tunnels:
        if item.id == tunnel_id:
            item.enable = not item.enable
            save_settings(settings)
            return item
    raise KeyError(f"tunnel not found: {tunnel_id}")


def get_tunnel(tunnel_id: str) -> Tunnel:
    for item in load_settings().tunnels:
        if item.id == tunnel_id:
            return item
    raise KeyError(f"tunnel not found: {tunnel_id}")
