from __future__ import annotations

import json

from app import storage


def test_load_legacy_settings_with_short_id(monkeypatch, tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "xray_path": r"C:\xray",
                "xray_service_name": "xray",
                "panel_host": "127.0.0.1",
                "panel_port": 18080,
                "public_address": "",
                "tunnels": [
                    {
                        "id": "legacy",
                        "name": "legacy",
                        "enable": True,
                        "listen": "0.0.0.0",
                        "port": 40000,
                        "protocol": "vmess",
                        "uuid": "my-home-xray",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(storage, "SETTINGS_FILE", settings_path)

    settings = storage.load_settings()

    assert len(settings.tunnels) == 1
    tunnel = settings.tunnels[0]
    assert tunnel.mode == "direct"
    assert tunnel.uuid == "717ca3f3-97cd-589b-b805-3acd24b97366"
    assert tunnel.kcp_uplink_capacity == 20
    assert tunnel.kcp_downlink_capacity == 100
