from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import Settings, Tunnel
from app.xray_config import (
    bridge_tag,
    build_a_side_text,
    build_xray_config,
    reverse_domain,
    reverse_outbound_tag,
)
from app.xray_runtime import xray_bin, xray_config_path


def test_build_config_keeps_direct_tunnels_compatible() -> None:
    settings = Settings(
        public_address="203.0.113.10",
        tunnels=[
            Tunnel(
                id="ssh",
                name="ssh",
                enable=True,
                mode="direct",
                port=40000,
                protocol="vless",
                uuid="11111111-1111-1111-1111-111111111111",
            ),
            Tunnel(
                id="web",
                name="web",
                enable=True,
                mode="direct",
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

    assert "reverse" not in config
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
            "uplinkCapacity": 5,
            "downlinkCapacity": 20,
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


def test_portal_builds_vmess_mkcp_bridge_and_preserves_a_target() -> None:
    tunnel = Tunnel(
        id="home",
        name="home",
        mode="portal",
        portal_address="a.example.net",
        portal_port=40000,
        target_address="127.0.0.1",
        target_port=18081,
        network="tcp,udp",
        protocol="vmess",
        uuid="11111111-1111-1111-1111-111111111111",
        kcp_final_mask_type="header-srtp",
    )

    config = build_xray_config(Settings(tunnels=[tunnel]))

    assert config["inbounds"] == []
    assert config["reverse"] == {
        "bridges": [
            {
                "tag": bridge_tag(tunnel),
                "domain": reverse_domain(tunnel),
            }
        ]
    }

    reverse_outbound = next(
        outbound for outbound in config["outbounds"] if outbound["tag"] == reverse_outbound_tag(tunnel)
    )
    assert reverse_outbound["protocol"] == "vmess"
    server = reverse_outbound["settings"]["vnext"][0]
    assert server["address"] == "a.example.net"
    assert server["port"] == 40000
    assert server["users"] == [
        {
            "id": tunnel.uuid,
            "alterId": 0,
            "security": "auto",
        }
    ]
    assert "mux" not in reverse_outbound
    assert reverse_outbound["streamSettings"]["network"] == "mkcp"
    assert reverse_outbound["streamSettings"]["finalmask"]["udp"][0]["type"] == "header-srtp"

    assert config["routing"]["rules"] == [
        {
            "type": "field",
            "domain": [f"full:{reverse_domain(tunnel)}"],
            "outboundTag": reverse_outbound_tag(tunnel),
        },
        {
            "type": "field",
            "inboundTag": [bridge_tag(tunnel)],
            "outboundTag": "direct",
        },
    ]


def test_direct_and_portal_can_coexist() -> None:
    direct = Tunnel(
        id="direct",
        mode="direct",
        port=40001,
        protocol="vmess",
        uuid="11111111-1111-1111-1111-111111111111",
    )
    portal = Tunnel(
        id="portal",
        mode="portal",
        portal_address="198.51.100.20",
        portal_port=40002,
        target_address="192.168.1.10",
        target_port=8080,
        protocol="vmess",
        uuid="22222222-2222-2222-2222-222222222222",
    )

    config = build_xray_config(Settings(tunnels=[direct, portal]))

    assert [item["tag"] for item in config["inbounds"]] == ["tunnel-in-direct"]
    assert len(config["reverse"]["bridges"]) == 1
    assert any(rule.get("inboundTag") == ["tunnel-in-direct"] for rule in config["routing"]["rules"])
    assert any(rule.get("inboundTag") == [bridge_tag(portal)] for rule in config["routing"]["rules"])


def test_legacy_settings_default_to_direct_and_migrate_finalmask() -> None:
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

    assert tunnel.mode == "direct"
    assert tunnel.kcp_uplink_capacity == 20
    assert tunnel.kcp_downlink_capacity == 100
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


def test_portal_rejects_vless() -> None:
    with pytest.raises(ValidationError, match="portal mode only supports vmess"):
        Tunnel(
            mode="portal",
            portal_address="a.example.net",
            protocol="vless",
        )


def test_a_side_text_is_mode_aware() -> None:
    direct = Tunnel(
        id="ssh",
        name="ssh",
        port=40000,
        protocol="vmess",
        uuid="11111111-1111-1111-1111-111111111111",
        kcp_final_mask_type="header-dtls",
    )
    direct_text = build_a_side_text(Settings(public_address="203.0.113.10"), direct)
    assert "A 端模式：公网直连" in direct_text
    assert "远端地址：203.0.113.10" in direct_text
    assert "远端端口：40000" in direct_text

    portal = Tunnel(
        id="portal",
        mode="portal",
        portal_address="a.example.net",
        portal_port=41000,
        target_address="127.0.0.1",
        target_port=18081,
        network="tcp",
        protocol="vmess",
        uuid="22222222-2222-2222-2222-222222222222",
    )
    portal_text = build_a_side_text(Settings(), portal)
    assert "A 端模式：Portal" in portal_text
    assert "A 端 Portal UDP 端口：41000" in portal_text
    assert "B 端目标：127.0.0.1:18081" in portal_text
    assert f"内部反向域名：{reverse_domain(portal)}" in portal_text


def test_windows_xray_paths_are_used() -> None:
    settings = Settings(xray_path=r"C:\xray")

    assert str(xray_bin(settings)).endswith("xray.exe")
    assert str(xray_config_path(settings)).endswith("config.json")
