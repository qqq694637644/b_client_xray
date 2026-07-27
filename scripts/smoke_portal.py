#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import Settings, Tunnel  # noqa: E402
from app.xray_config import build_xray_config, reverse_domain  # noqa: E402

UUID = "11111111-1111-1111-1111-111111111111"
PAYLOAD = b"vmess-mkcp-portal-smoke"


class EchoServer:
    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp.bind(("127.0.0.1", 0))
        self.port = self.tcp.getsockname()[1]
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(("127.0.0.1", self.port))
        self.tcp.listen()
        self.tcp.settimeout(0.5)
        self.udp.settimeout(0.5)
        self.threads = [
            threading.Thread(target=self._serve_tcp, daemon=True),
            threading.Thread(target=self._serve_udp, daemon=True),
        ]

    def start(self) -> None:
        for thread in self.threads:
            thread.start()

    def close(self) -> None:
        self.stop_event.set()
        self.tcp.close()
        self.udp.close()
        for thread in self.threads:
            thread.join(timeout=2)

    def _serve_tcp(self) -> None:
        while not self.stop_event.is_set():
            try:
                conn, _ = self.tcp.accept()
            except (TimeoutError, OSError):
                continue
            threading.Thread(target=self._echo_tcp, args=(conn,), daemon=True).start()

    @staticmethod
    def _echo_tcp(conn: socket.socket) -> None:
        with conn:
            try:
                while True:
                    data = conn.recv(65535)
                    if not data:
                        return
                    conn.sendall(data)
            except OSError:
                return

    def _serve_udp(self) -> None:
        while not self.stop_event.is_set():
            try:
                data, address = self.udp.recvfrom(65535)
            except (TimeoutError, OSError):
                continue
            self.udp.sendto(data, address)


def find_dual_port() -> int:
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        tcp.bind(("127.0.0.1", 0))
        port = tcp.getsockname()[1]
        udp.bind(("127.0.0.1", port))
        return port
    finally:
        tcp.close()
        udp.close()


def find_udp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def xray_version(xray: Path) -> str:
    for args in ([str(xray), "version"], [str(xray), "-version"]):
        completed = subprocess.run(args, capture_output=True, text=True, check=False, timeout=20)
        output = f"{completed.stdout}\n{completed.stderr}".strip()
        if completed.returncode == 0 and output:
            return output
    raise RuntimeError(f"cannot read Xray version from {xray}")


def make_a_config(business_port: int, portal_port: int, target_port: int) -> dict:
    domain = f"reverse-{UUID}.xui.internal"
    return {
        "log": {"loglevel": "warning"},
        "reverse": {"portals": [{"tag": "portal-smoke", "domain": domain}]},
        "inbounds": [
            {
                "tag": "business-smoke",
                "listen": "127.0.0.1",
                "port": business_port,
                "protocol": "dokodemo-door",
                "settings": {
                    "address": "127.0.0.1",
                    "port": target_port,
                    "network": "tcp,udp",
                },
            },
            {
                "tag": "portal-listener-smoke",
                "listen": "127.0.0.1",
                "port": portal_port,
                "protocol": "vmess",
                "settings": {
                    "clients": [
                        {
                            "id": UUID,
                            "alterId": 0,
                            "email": "portal-smoke",
                        }
                    ]
                },
                "streamSettings": {
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
                    "finalmask": {
                        "udp": [{"type": "header-srtp", "settings": {}}]
                    },
                },
            },
        ],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom", "settings": {}},
            {"tag": "blocked", "protocol": "blackhole", "settings": {}},
        ],
        "routing": {
            "rules": [
                {
                    "type": "field",
                    "inboundTag": ["business-smoke"],
                    "outboundTag": "portal-smoke",
                },
                {
                    "type": "field",
                    "domain": [f"full:{domain}"],
                    "outboundTag": "portal-smoke",
                },
            ]
        },
    }


def make_b_config(portal_port: int, target_port: int) -> dict:
    tunnel = Tunnel(
        id="smoke",
        name="smoke",
        mode="portal",
        portal_address="127.0.0.1",
        portal_port=portal_port,
        target_address="127.0.0.1",
        target_port=target_port,
        network="tcp,udp",
        protocol="vmess",
        uuid=UUID,
        kcp_final_mask_type="header-srtp",
        kcp_mtu=1350,
        kcp_tti=20,
        kcp_uplink_capacity=5,
        kcp_downlink_capacity=20,
        kcp_read_buffer_size=2,
        kcp_write_buffer_size=2,
    )
    if reverse_domain(tunnel) != f"reverse-{UUID}.xui.internal":
        raise RuntimeError("B reverse domain does not match A")
    return build_xray_config(Settings(tunnels=[tunnel]))


class XrayProcess:
    def __init__(self, xray: Path, config: Path, log: Path) -> None:
        self.log_handle = log.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(xray), "run", "-config", str(config)],
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.log = log

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.log_handle.close()

    def ensure_running(self) -> None:
        code = self.process.poll()
        if code is not None:
            raise RuntimeError(f"Xray exited with code {code}; log:\n{tail(self.log)}")


def tail(path: Path, lines: int = 120) -> str:
    if not path.exists():
        return "<missing log>"
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])


def assert_tcp_udp_echo(port: int) -> None:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as sock:
        sock.settimeout(3)
        sock.sendall(PAYLOAD)
        received = sock.recv(len(PAYLOAD))
        if received != PAYLOAD:
            raise RuntimeError(f"TCP echo mismatch: {received!r}")

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp.settimeout(3)
        udp.sendto(PAYLOAD, ("127.0.0.1", port))
        received, _ = udp.recvfrom(65535)
        if received != PAYLOAD:
            raise RuntimeError(f"UDP echo mismatch: {received!r}")
    finally:
        udp.close()


def wait_for_echo(port: int, processes: list[XrayProcess], timeout: int = 25) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        for process in processes:
            process.ensure_running()
        try:
            assert_tcp_udp_echo(port)
            return
        except (OSError, RuntimeError) as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"TCP/UDP echo did not succeed within {timeout}s: {last_error}")


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start A Portal and B Bridge with Xray v26.3.27 and verify TCP/UDP plus reconnects."
    )
    parser.add_argument("--xray", required=True, type=Path, help="Path to the Xray v26.3.27 binary")
    args = parser.parse_args()
    xray = args.xray.resolve()
    if not xray.exists():
        raise FileNotFoundError(xray)

    version = xray_version(xray)
    if "26.3.27" not in version:
        raise RuntimeError(f"expected Xray 26.3.27, got:\n{version}")
    print(version.splitlines()[0])

    echo = EchoServer()
    echo.start()
    business_port = find_dual_port()
    portal_port = find_udp_port()

    with tempfile.TemporaryDirectory(prefix="xray-portal-smoke-") as temp_dir:
        temp = Path(temp_dir)
        a_config = temp / "a.json"
        b_config = temp / "b.json"
        write_json(a_config, make_a_config(business_port, portal_port, echo.port))
        write_json(b_config, make_b_config(portal_port, echo.port))

        subprocess.run(
            [str(xray), "run", "-test", "-config", str(a_config)],
            check=True,
            timeout=30,
        )
        subprocess.run(
            [str(xray), "run", "-test", "-config", str(b_config)],
            check=True,
            timeout=30,
        )

        a: XrayProcess | None = None
        b: XrayProcess | None = None
        try:
            a = XrayProcess(xray, a_config, temp / "a.log")
            b = XrayProcess(xray, b_config, temp / "b.log")
            wait_for_echo(business_port, [a, b])
            print("initial TCP/UDP portal echo: OK")

            b.stop()
            b = XrayProcess(xray, b_config, temp / "b-restart.log")
            wait_for_echo(business_port, [a, b])
            print("B restart and reconnect: OK")

            a.stop()
            a = XrayProcess(xray, a_config, temp / "a-restart.log")
            # A UDP restart can leave the old mKCP session alive until its
            # inactivity timeout. Give the existing B process enough time to
            # detect that loss and create a fresh reverse worker by itself.
            wait_for_echo(business_port, [a, b], timeout=75)
            print("A restart and B reconnect: OK")
        except Exception:
            for label, process in (("A", a), ("B", b)):
                if process is not None:
                    print(f"--- {label} log ---\n{tail(process.log)}", file=sys.stderr)
            raise
        finally:
            if b is not None:
                b.stop()
            if a is not None:
                a.stop()
            echo.close()

    print("VMess/mKCP Portal smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
