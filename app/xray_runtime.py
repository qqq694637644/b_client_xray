from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models import CommandResult, Settings
from app.xray_config import build_xray_config

COMMAND_TIMEOUT = 30
SERVICE_WAIT_SECONDS = 10
SERVICE_STABLE_SECONDS = 2
SERVICE_STATE_CODES = {
    "STOPPED": "1",
    "RUNNING": "4",
}


def xray_bin(settings: Settings) -> Path:
    return Path(settings.xray_path) / "xray.exe"


def xray_config_path(settings: Settings) -> Path:
    return Path(settings.xray_path) / "config.json"


def run_command(args: list[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(ok=False, stdout=exc.stdout or "", stderr="command timed out")
    except FileNotFoundError as exc:
        return CommandResult(ok=False, stdout="", stderr=str(exc))
    return CommandResult(
        ok=completed.returncode == 0,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def validate_config(settings: Settings, config: dict[str, Any] | None = None) -> CommandResult:
    config = config if config is not None else build_xray_config(settings)
    xray_dir = Path(settings.xray_path)
    if not xray_dir.is_dir():
        return CommandResult(ok=False, stderr=f"Xray directory not found: {xray_dir}")
    bin_path = xray_bin(settings)
    if not bin_path.exists():
        return CommandResult(ok=False, stderr=f"xray.exe not found: {bin_path}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=xray_dir,
            prefix=".config.x-ui-test.",
            suffix=".json",
            delete=False,
        ) as temp_file:
            json.dump(config, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            tmp_path = Path(temp_file.name)
        return run_command([str(bin_path), "run", "-test", "-config", str(tmp_path)])
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def write_config_atomically(settings: Settings, config: dict[str, Any]) -> Path | None:
    config_path = xray_config_path(settings)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None

    if config_path.exists():
        backup_path = config_path.with_name(
            f"config.json.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        shutil.copy2(config_path, backup_path)

    fd, tmp_name = tempfile.mkstemp(
        dir=config_path.parent,
        prefix=".config.x-ui.tmp.",
        suffix=".json",
    )
    tmp_path = Path(tmp_name)
    ok = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(config, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
        os.replace(tmp_path, config_path)
        ok = True
        return backup_path
    finally:
        if not ok:
            tmp_path.unlink(missing_ok=True)


def save_config(settings: Settings) -> CommandResult:
    config = build_xray_config(settings)
    validation = validate_config(settings, config)
    if not validation.ok:
        return validation
    backup_path = write_config_atomically(settings, config)
    suffix = f"\nbackup: {backup_path}" if backup_path else ""
    return CommandResult(ok=True, stdout=f"saved: {xray_config_path(settings)}{suffix}")


def service_status(settings: Settings) -> CommandResult:
    return run_command(["sc.exe", "query", settings.xray_service_name])


def _service_state_code(result: CommandResult) -> str | None:
    output = f"{result.stdout}\n{result.stderr}"
    for line in output.splitlines():
        if "STATE" not in line.upper() or ":" not in line:
            continue
        value = line.split(":", 1)[1].strip().split()
        if value and value[0].isdigit():
            return value[0]
    return None


def _service_is_in_state(result: CommandResult, state: str) -> bool:
    expected = SERVICE_STATE_CODES.get(state.upper())
    return expected is not None and _service_state_code(result) == expected


def _wait_for_service_state(settings: Settings, state: str) -> CommandResult:
    state = state.upper()
    last = CommandResult(ok=False, stderr="service state was not queried")
    for _ in range(SERVICE_WAIT_SECONDS):
        last = service_status(settings)
        if _service_is_in_state(last, state):
            return CommandResult(ok=True, stdout=last.stdout, stderr=last.stderr)
        time.sleep(1)
    return CommandResult(
        ok=False,
        stdout=last.stdout,
        stderr=f"service did not reach {state} within {SERVICE_WAIT_SECONDS}s\n{last.stderr}",
    )


def restart_service(settings: Settings) -> CommandResult:
    stop = run_command(["sc.exe", "stop", settings.xray_service_name])
    stopped = _wait_for_service_state(settings, "STOPPED")
    if not stopped.ok:
        return CommandResult(
            ok=False,
            stdout=f"stop:\n{stop.stdout}\nstatus:\n{stopped.stdout}",
            stderr=f"stop:\n{stop.stderr}\nstatus:\n{stopped.stderr}",
        )

    start = run_command(["sc.exe", "start", settings.xray_service_name])
    if not start.ok:
        return CommandResult(
            ok=False,
            stdout=f"stop:\n{stop.stdout}\nstart:\n{start.stdout}",
            stderr=f"stop:\n{stop.stderr}\nstart:\n{start.stderr}",
        )

    running = _wait_for_service_state(settings, "RUNNING")
    if not running.ok:
        return CommandResult(
            ok=False,
            stdout=f"stop:\n{stop.stdout}\nstart:\n{start.stdout}\nstatus:\n{running.stdout}",
            stderr=f"stop:\n{stop.stderr}\nstart:\n{start.stderr}\nstatus:\n{running.stderr}",
        )

    time.sleep(SERVICE_STABLE_SECONDS)
    stable = service_status(settings)
    if not _service_is_in_state(stable, "RUNNING"):
        return CommandResult(
            ok=False,
            stdout=(
                f"stop:\n{stop.stdout}\nstart:\n{start.stdout}\n"
                f"running:\n{running.stdout}\nstable check:\n{stable.stdout}"
            ),
            stderr=(
                f"Xray service left RUNNING state within {SERVICE_STABLE_SECONDS}s.\n"
                f"stop:\n{stop.stderr}\nstart:\n{start.stderr}\n"
                f"running:\n{running.stderr}\nstable check:\n{stable.stderr}"
            ),
        )

    return CommandResult(
        ok=True,
        stdout=(
            f"stop:\n{stop.stdout}\nstart:\n{start.stdout}\n"
            f"running:\n{running.stdout}\nstable check:\n{stable.stdout}"
        ),
        stderr=f"stop:\n{stop.stderr}\nstart:\n{start.stderr}",
    )


def restore_backup(settings: Settings, backup_path: Path | None) -> None:
    config_path = xray_config_path(settings)
    if backup_path is None:
        config_path.unlink(missing_ok=True)
        return
    shutil.copy2(backup_path, config_path)


def apply_config(settings: Settings) -> CommandResult:
    config = build_xray_config(settings)
    validation = validate_config(settings, config)
    if not validation.ok:
        return validation

    backup_path = write_config_atomically(settings, config)
    restart = restart_service(settings)
    if restart.ok:
        return restart

    restore_error = ""
    try:
        restore_backup(settings, backup_path)
        restore_restart = restart_service(settings)
        if not restore_restart.ok:
            restore_error = f"\nrestore restart failed:\n{restore_restart.stderr}"
    except Exception as exc:  # pragma: no cover - defensive rollback reporting
        restore_error = f"\nrestore failed: {exc}"

    return CommandResult(
        ok=False,
        stdout=restart.stdout,
        stderr=f"restart failed; old config restored if possible.\n{restart.stderr}{restore_error}",
    )
