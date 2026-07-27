from __future__ import annotations

import json

from app.models import CommandResult, Settings
from app import xray_runtime


def sc_status(state_code: int, state_name: str) -> CommandResult:
    return CommandResult(
        ok=True,
        stdout=f"SERVICE_NAME: xray\n        STATE              : {state_code}  {state_name}\n",
    )


def test_restart_service_waits_for_stable_running(monkeypatch) -> None:
    settings = Settings(xray_service_name="xray")
    commands = iter(
        [
            CommandResult(ok=True, stdout="stop requested"),
            CommandResult(ok=True, stdout="start requested"),
        ]
    )
    statuses = iter(
        [
            sc_status(1, "STOPPED"),
            sc_status(4, "RUNNING"),
            sc_status(4, "RUNNING"),
        ]
    )
    monkeypatch.setattr(xray_runtime, "run_command", lambda _args: next(commands))
    monkeypatch.setattr(xray_runtime, "service_status", lambda _settings: next(statuses))
    monkeypatch.setattr(xray_runtime.time, "sleep", lambda _seconds: None)

    result = xray_runtime.restart_service(settings)

    assert result.ok is True
    assert "stable check" in result.stdout


def test_restart_service_rejects_immediate_exit(monkeypatch) -> None:
    settings = Settings(xray_service_name="xray")
    commands = iter(
        [
            CommandResult(ok=True, stdout="stop requested"),
            CommandResult(ok=True, stdout="start requested"),
        ]
    )
    statuses = iter(
        [
            sc_status(1, "STOPPED"),
            sc_status(4, "RUNNING"),
            sc_status(1, "STOPPED"),
        ]
    )
    monkeypatch.setattr(xray_runtime, "run_command", lambda _args: next(commands))
    monkeypatch.setattr(xray_runtime, "service_status", lambda _settings: next(statuses))
    monkeypatch.setattr(xray_runtime.time, "sleep", lambda _seconds: None)

    result = xray_runtime.restart_service(settings)

    assert result.ok is False
    assert "left RUNNING state" in result.stderr


def test_restart_service_fails_when_running_is_never_reached(monkeypatch) -> None:
    settings = Settings(xray_service_name="xray")
    commands = iter(
        [
            CommandResult(ok=True, stdout="stop requested"),
            CommandResult(ok=True, stdout="start requested"),
        ]
    )
    statuses = iter(
        [
            sc_status(1, "STOPPED"),
            sc_status(1, "STOPPED"),
            sc_status(1, "STOPPED"),
        ]
    )
    monkeypatch.setattr(xray_runtime, "SERVICE_WAIT_SECONDS", 2)
    monkeypatch.setattr(xray_runtime, "run_command", lambda _args: next(commands))
    monkeypatch.setattr(xray_runtime, "service_status", lambda _settings: next(statuses))
    monkeypatch.setattr(xray_runtime.time, "sleep", lambda _seconds: None)

    result = xray_runtime.restart_service(settings)

    assert result.ok is False
    assert "did not reach RUNNING" in result.stderr


def test_apply_config_restores_old_config_after_unstable_start(monkeypatch, tmp_path) -> None:
    settings = Settings(xray_path=str(tmp_path), xray_service_name="xray")
    config_path = tmp_path / "config.json"
    old_config = {"marker": "old"}
    config_path.write_text(json.dumps(old_config), encoding="utf-8")

    monkeypatch.setattr(xray_runtime, "build_xray_config", lambda _settings: {"marker": "new"})
    monkeypatch.setattr(
        xray_runtime,
        "validate_config",
        lambda _settings, _config: CommandResult(ok=True),
    )
    restarts = iter(
        [
            CommandResult(ok=False, stderr="service exited immediately"),
            CommandResult(ok=True, stdout="old service restored"),
        ]
    )
    monkeypatch.setattr(xray_runtime, "restart_service", lambda _settings: next(restarts))

    result = xray_runtime.apply_config(settings)

    assert result.ok is False
    assert json.loads(config_path.read_text(encoding="utf-8")) == old_config
    assert "old config restored" in result.stderr
