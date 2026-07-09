from __future__ import annotations

from app.models import Settings, Tunnel
from app.xray_config import build_a_side_text, build_xray_config
from app.xray_runtime import xray_bin, xray_config_path


def test_build_config_merges_multiple_enabled_tunnels() -> None:
    settings = Settings(
        public_address="203.0.113.10",
        tunnels=[
            Tunnel(
                id="ssh",
                name="ssh",
                enable=True,
                port=40000,
                protocol="vless",
                uuid="11111111-1111-1111-1111-111111111111",
            ),
            Tunnel(
                id="web",
                name="web",
                enable=True,
                port=40001,
                protocol="vmess",
                uuid="22222222-2222-2222-2222-222222222222",
                kcp_final_mask_type="header-srtp",
            ),
            Tunnel(
                id="disabled",
                name="disabled",
                enable=False,
                port=40002,
                protocol="vless",
                uuid="33333333-3333-3333-3333-333333333333",
            ),
        ],
    )

    config = build_xray_config(settings)

    assert len(config["inbounds"]) == 2
    assert [item["tag"] for item in config["inbounds"]] == ["tunnel-in-ssh", "tunnel-in-web"]
    assert config["outbounds"][0]["tag"] == "direct"
    assert config["outbounds"][0]["protocol"] == "freedom"
    assert config["routing"]["rules"] == [
        {"type": "field", "inboundTag": ["tunnel-in-ssh"], "outboundTag": "direct"},
        {"type": "field", "inboundTag": ["tunnel-in-web"], "outboundTag": "direct"},
    ]

    vless = config["inbounds"][0]
    assert vless["protocol"] == "vless"
    assert vless["settings"]["decryption"] == "none"
    assert vless["streamSettings"] == {
        "network": "mkcp",
        "security": "none",
        "kcpSettings": {
            "mtu": 1350,
            "tti": 20,
            "uplinkCapacity": 20,
            "downlinkCapacity": 100,
            "congestion": False,
            "readBufferSize": 2,
            "writeBufferSize": 2,
        },
    }

    vmess = config["inbounds"][1]
    assert vmess["protocol"] == "vmess"
    assert vmess["settings"]["clients"][0]["alterId"] == 0
    assert "header" not in vmess["streamSettings"]["kcpSettings"]
    assert "seed" not in vmess["streamSettings"]["kcpSettings"]
    assert vmess["streamSettings"]["finalmask"] == {
        "udp": [
            {
                "type": "header-srtp",
                "settings": {},
            }
        ]
    }


def test_legacy_kcp_header_is_migrated_to_finalmask_type() -> None:
    tunnel = Tunnel(
        id="legacy",
        name="legacy",
        port=40000,
        protocol="vless",
        uuid="11111111-1111-1111-1111-111111111111",
        kcp_header_type="wechat-video",
        kcp_seed="legacy-seed",
    )

    config = build_xray_config(Settings(tunnels=[tunnel]))
    stream_settings = config["inbounds"][0]["streamSettings"]

    assert stream_settings["network"] == "mkcp"
    assert "header" not in stream_settings["kcpSettings"]
    assert "seed" not in stream_settings["kcpSettings"]
    assert stream_settings["finalmask"] == {
        "udp": [
            {
                "type": "header-wechat",
                "settings": {},
            }
        ]
    }


def test_a_side_text_contains_per_tunnel_connection_params() -> None:
    settings = Settings(public_address="203.0.113.10")
    tunnel = Tunnel(
        id="ssh",
        name="ssh",
        port=40000,
        protocol="vless",
        uuid="11111111-1111-1111-1111-111111111111",
        kcp_final_mask_type="header-dtls",
    )

    text = build_a_side_text(settings, tunnel)

    assert "协议：vless" in text
    assert "远端地址：203.0.113.10" in text
    assert "远端端口：40000" in text
    assert "UUID：11111111-1111-1111-1111-111111111111" in text
    assert "FinalMask UDP header：header-dtls" in text


def test_windows_xray_paths_are_used() -> None:
    settings = Settings(xray_path=r"C:\xray")

    assert str(xray_bin(settings)).endswith("xray.exe")
    assert str(xray_config_path(settings)).endswith("config.json")
