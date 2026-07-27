from __future__ import annotations

from typing import Any

from app.models import Settings, Tunnel


def direct_inbound_tag(tunnel: Tunnel) -> str:
    return f"tunnel-in-{tunnel.id}"


def bridge_tag(tunnel: Tunnel) -> str:
    return f"tunnel-bridge-{tunnel.id}"


def reverse_outbound_tag(tunnel: Tunnel) -> str:
    return f"tunnel-reverse-{tunnel.id}"


def reverse_domain(tunnel: Tunnel) -> str:
    # Must exactly match x-ui's deterministic internal domain. It is an Xray
    # routing key, not a DNS name and does not need to resolve.
    return f"reverse-{tunnel.uuid}.xui.internal"


def format_host_port(address: str, port: int) -> str:
    if ":" in address and not address.startswith("["):
        return f"[{address}]:{port}"
    return f"{address}:{port}"


def build_kcp_finalmask(mask_type: str) -> dict[str, Any] | None:
    mask_type = mask_type.strip()
    if mask_type == "" or mask_type == "none":
        return None
    return {
        "udp": [
            {
                "type": mask_type,
                "settings": {},
            }
        ]
    }


def build_stream_settings(tunnel: Tunnel) -> dict[str, Any]:
    stream_settings: dict[str, Any] = {
        "network": "mkcp",
        "security": "none",
        "kcpSettings": {
            "mtu": tunnel.kcp_mtu,
            "tti": tunnel.kcp_tti,
            "uplinkCapacity": tunnel.kcp_uplink_capacity,
            "downlinkCapacity": tunnel.kcp_downlink_capacity,
            "congestion": tunnel.kcp_congestion,
            "readBufferSize": tunnel.kcp_read_buffer_size,
            "writeBufferSize": tunnel.kcp_write_buffer_size,
        },
    }

    finalmask = build_kcp_finalmask(tunnel.kcp_final_mask_type)
    if finalmask is not None:
        stream_settings["finalmask"] = finalmask

    return stream_settings


def build_direct_inbound(tunnel: Tunnel) -> dict[str, Any]:
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
        "tag": direct_inbound_tag(tunnel),
        "listen": tunnel.listen,
        "port": tunnel.port,
        "protocol": tunnel.protocol,
        "settings": settings,
        "streamSettings": build_stream_settings(tunnel),
    }


def build_direct_routing_rule(tunnel: Tunnel) -> dict[str, Any]:
    return {
        "type": "field",
        "inboundTag": [direct_inbound_tag(tunnel)],
        "outboundTag": "direct",
    }


def build_reverse_outbound(tunnel: Tunnel) -> dict[str, Any]:
    return {
        "tag": reverse_outbound_tag(tunnel),
        "protocol": "vmess",
        "settings": {
            "vnext": [
                {
                    "address": tunnel.portal_address,
                    "port": tunnel.portal_port,
                    "users": [
                        {
                            "id": tunnel.uuid,
                            "alterId": 0,
                            "security": "auto",
                        }
                    ],
                }
            ]
        },
        "streamSettings": build_stream_settings(tunnel),
    }


def build_bridge_config(tunnel: Tunnel) -> dict[str, Any]:
    return {
        "tag": bridge_tag(tunnel),
        "domain": reverse_domain(tunnel),
    }


def build_portal_routing_rules(tunnel: Tunnel) -> list[dict[str, Any]]:
    return [
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


def build_xray_config(settings: Settings) -> dict[str, Any]:
    enabled_tunnels = [tunnel for tunnel in settings.tunnels if tunnel.enable]
    direct_tunnels = [tunnel for tunnel in enabled_tunnels if tunnel.mode == "direct"]
    portal_tunnels = [tunnel for tunnel in enabled_tunnels if tunnel.mode == "portal"]

    outbounds: list[dict[str, Any]] = [
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
    ]
    for tunnel in portal_tunnels:
        outbounds.append(build_reverse_outbound(tunnel))

    routing_rules = [build_direct_routing_rule(tunnel) for tunnel in direct_tunnels]
    for tunnel in portal_tunnels:
        routing_rules.extend(build_portal_routing_rules(tunnel))

    config: dict[str, Any] = {
        "log": {
            "loglevel": "warning",
        },
        "inbounds": [build_direct_inbound(tunnel) for tunnel in direct_tunnels],
        "outbounds": outbounds,
        "routing": {
            "rules": routing_rules,
        },
    }
    if portal_tunnels:
        config["reverse"] = {
            "bridges": [build_bridge_config(tunnel) for tunnel in portal_tunnels],
        }
    return config


def build_a_side_text(settings: Settings, tunnel: Tunnel) -> str:
    common = [
        f"模式：{tunnel.mode}",
        f"协议：{tunnel.protocol}",
        f"UUID：{tunnel.uuid}",
        "传输：mKCP",
        f"FinalMask UDP header：{tunnel.kcp_final_mask_type}",
        f"mtu：{tunnel.kcp_mtu}",
        f"tti：{tunnel.kcp_tti}",
        f"uplinkCapacity：{tunnel.kcp_uplink_capacity}",
        f"downlinkCapacity：{tunnel.kcp_downlink_capacity}",
        f"congestion：{str(tunnel.kcp_congestion).lower()}",
        f"readBufferSize：{tunnel.kcp_read_buffer_size}",
        f"writeBufferSize：{tunnel.kcp_write_buffer_size}",
    ]
    if tunnel.mode == "portal":
        details = [
            "A 端模式：Portal",
            f"A 端 Portal UDP 端口：{tunnel.portal_port}",
            f"B 端连接 A 地址：{tunnel.portal_address}",
            f"B 端目标：{format_host_port(tunnel.target_address, tunnel.target_port)}",
            f"入口网络：{tunnel.network}",
            f"内部反向域名：{reverse_domain(tunnel)}",
        ]
    else:
        details = [
            "A 端模式：公网直连",
            f"远端地址：{settings.public_address}",
            f"远端端口：{tunnel.port}",
        ]
    return "\n".join(details + common)
