from __future__ import annotations

from typing import Any

from app.models import Settings, Tunnel


def tunnel_tag(tunnel: Tunnel) -> str:
    return f"tunnel-in-{tunnel.id}"


def build_inbound(tunnel: Tunnel) -> dict[str, Any]:
    if tunnel.protocol == "vless":
        settings: dict[str, Any] = {
            "clients": [
                {
                    "id": tunnel.uuid,
                    "email": tunnel.name or tunnel.id,
                }
            ],
            "decryption": "none",
        }
    else:
        settings = {
            "clients": [
                {
                    "id": tunnel.uuid,
                    "alterId": 0,
                    "email": tunnel.name or tunnel.id,
                }
            ]
        }

    return {
        "tag": tunnel_tag(tunnel),
        "listen": tunnel.listen,
        "port": tunnel.port,
        "protocol": tunnel.protocol,
        "settings": settings,
        "streamSettings": {
            "network": "kcp",
            "security": "none",
            "kcpSettings": {
                "mtu": tunnel.kcp_mtu,
                "tti": tunnel.kcp_tti,
                "uplinkCapacity": tunnel.kcp_uplink_capacity,
                "downlinkCapacity": tunnel.kcp_downlink_capacity,
                "congestion": tunnel.kcp_congestion,
                "readBufferSize": tunnel.kcp_read_buffer_size,
                "writeBufferSize": tunnel.kcp_write_buffer_size,
                "header": {
                    "type": tunnel.kcp_header_type,
                },
                "seed": tunnel.kcp_seed,
            },
        },
    }


def build_routing_rule(tunnel: Tunnel) -> dict[str, Any]:
    return {
        "type": "field",
        "inboundTag": [tunnel_tag(tunnel)],
        "outboundTag": "direct",
    }


def build_xray_config(settings: Settings) -> dict[str, Any]:
    enabled_tunnels = [tunnel for tunnel in settings.tunnels if tunnel.enable]
    return {
        "log": {
            "loglevel": "warning",
        },
        "inbounds": [build_inbound(tunnel) for tunnel in enabled_tunnels],
        "outbounds": [
            {
                "tag": "direct",
                "protocol": "freedom",
                "settings": {},
            },
            {
                "tag": "blocked",
                "protocol": "blackhole",
                "settings": {},
            },
        ],
        "routing": {
            "rules": [build_routing_rule(tunnel) for tunnel in enabled_tunnels],
        },
    }


def build_a_side_text(settings: Settings, tunnel: Tunnel) -> str:
    return "\n".join(
        [
            f"协议：{tunnel.protocol}",
            f"远端地址：{settings.public_address}",
            f"远端端口：{tunnel.port}",
            f"UUID：{tunnel.uuid}",
            "传输：mKCP",
            f"header type：{tunnel.kcp_header_type}",
            f"seed：{tunnel.kcp_seed}",
            f"mtu：{tunnel.kcp_mtu}",
            f"tti：{tunnel.kcp_tti}",
            f"uplinkCapacity：{tunnel.kcp_uplink_capacity}",
            f"downlinkCapacity：{tunnel.kcp_downlink_capacity}",
            f"congestion：{str(tunnel.kcp_congestion).lower()}",
            f"readBufferSize：{tunnel.kcp_read_buffer_size}",
            f"writeBufferSize：{tunnel.kcp_write_buffer_size}",
        ]
    )
