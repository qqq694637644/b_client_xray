from __future__ import annotations

import secrets
import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Protocol = Literal["vless", "vmess"]
KcpHeaderType = Literal["none", "srtp", "utp", "wechat-video", "dtls", "wireguard"]


def new_tunnel_id() -> str:
    return f"tunnel-{secrets.token_hex(4)}"


def new_uuid() -> str:
    return str(uuid.uuid4())


def new_seed() -> str:
    return secrets.token_urlsafe(12)


class Tunnel(BaseModel):
    id: str = Field(default_factory=new_tunnel_id)
    name: str = "default"
    enable: bool = True
    listen: str = "0.0.0.0"
    port: int = 40000
    protocol: Protocol = "vless"
    uuid: str = Field(default_factory=new_uuid)
    kcp_header_type: KcpHeaderType = "none"
    kcp_seed: str = Field(default_factory=new_seed)
    kcp_mtu: int = 1350
    kcp_tti: int = 20
    kcp_uplink_capacity: int = 20
    kcp_downlink_capacity: int = 100
    kcp_congestion: bool = False
    kcp_read_buffer_size: int = 2
    kcp_write_buffer_size: int = 2
    remark: str = ""

    @field_validator("name", "listen", "uuid", "kcp_seed")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("port")
    @classmethod
    def check_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("port must be between 1 and 65535")
        return value

    @field_validator("kcp_mtu", "kcp_uplink_capacity", "kcp_downlink_capacity", "kcp_read_buffer_size", "kcp_write_buffer_size")
    @classmethod
    def check_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be greater than 0")
        return value

    @field_validator("kcp_tti")
    @classmethod
    def check_tti(cls, value: int) -> int:
        if value < 10 or value > 5000:
            raise ValueError("kcp_tti must be between 10 and 5000")
        return value


class Settings(BaseModel):
    xray_path: str = r"C:\xray"
    xray_service_name: str = "xray"
    panel_host: str = "127.0.0.1"
    panel_port: int = 18080
    public_address: str = ""
    tunnels: list[Tunnel] = Field(default_factory=list)

    @field_validator("xray_path", "xray_service_name", "panel_host", "public_address")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("panel_port")
    @classmethod
    def check_panel_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("panel_port must be between 1 and 65535")
        return value


class SettingsUpdate(BaseModel):
    xray_path: str
    xray_service_name: str
    panel_host: str = "127.0.0.1"
    panel_port: int = 18080
    public_address: str = ""


class CommandResult(BaseModel):
    ok: bool
    stdout: str = ""
    stderr: str = ""


class Status(BaseModel):
    xray_path: str
    xray_config: str
    xray_service_name: str
    tunnel_count: int
    enabled_tunnel_count: int
    service_active: str
