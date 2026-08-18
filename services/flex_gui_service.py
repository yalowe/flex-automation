from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_WM_CYCLE_MS = "1000"
DEFAULT_DM_LITERS_PER_PULSE = 1.0


def load_wm_settings(settings_path: str | Path) -> dict[str, dict[str, str | bool]]:
    path = Path(settings_path)
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(raw, dict):
        return {}

    return raw


def build_wm_settings_payload(
    config_data: dict,
    existing_settings: dict[str, dict[str, str | bool]] | None = None,
) -> dict[str, dict[str, str | bool]]:
    existing_settings = existing_settings or {}
    dosing_channels = config_data.get("dosing_channels", {}) or {}
    dm_liters_per_pulse = _read_dm_liters_per_pulse(
        existing_settings.get("dm_liters_per_pulse")
    )

    payload: dict[str, dict[str, str | bool]] = {}

    for wm_id in range(1, 6):
        existing_entry = existing_settings.get(str(wm_id), {})
        payload[str(wm_id)] = {
            "show": bool(existing_entry.get("show", True)),
            "cycle_ms": str(existing_entry.get("cycle_ms", DEFAULT_WM_CYCLE_MS)),
        }

    wm_cycle = int(config_data.get("wm_cycle") or 0)
    if wm_cycle > 0:
        payload["1"] = {
            "show": True,
            "cycle_ms": str(wm_cycle),
        }

    for channel_id in range(1, 5):
        wm_id = channel_id + 1
        channel_data = dosing_channels.get(channel_id, {}) or {}
        dm_flow_lph = float(channel_data.get("flow") or 0)
        dm_cycle = (
            (dm_liters_per_pulse * 3600000) / dm_flow_lph
            if dm_flow_lph > 0 and dm_liters_per_pulse > 0
            else 0
        )
        payload[str(wm_id)] = {
            "show": bool(channel_data.get("enabled", False)),
            "cycle_ms": (
                _format_cycle_ms(dm_cycle) if dm_cycle > 0 else DEFAULT_WM_CYCLE_MS
            ),
        }

    payload["dm_liters_per_pulse"] = dm_liters_per_pulse
    return payload


def _format_cycle_ms(cycle_ms: float) -> str:
    return f"{cycle_ms:.2f}".rstrip("0").rstrip(".")


def _read_dm_liters_per_pulse(value: object) -> float:
    try:
        liters_per_pulse = float(value)
    except (TypeError, ValueError):
        return DEFAULT_DM_LITERS_PER_PULSE

    return liters_per_pulse if liters_per_pulse > 0 else DEFAULT_DM_LITERS_PER_PULSE


def write_wm_settings(
    settings_path: str | Path,
    payload: dict[str, dict[str, str | bool]],
) -> None:
    path = Path(settings_path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlexGuiSession:
    def __init__(
        self,
        *,
        launcher_script: str | Path,
        port: str,
        baud: int,
        wm_settings_path: str | Path,
    ):
        self.launcher_script = Path(launcher_script)
        self.port = port
        self.baud = baud
        self.wm_settings_path = Path(wm_settings_path)
        self._process: subprocess.Popen[str] | None = None

    def launch(self) -> None:
        self._restart_gui()

    def prepare_for_program(self, config_data: dict) -> None:
        existing = load_wm_settings(self.wm_settings_path)
        payload = build_wm_settings_payload(config_data, existing)
        write_wm_settings(self.wm_settings_path, payload)
        self._restart_gui()

    def close(self) -> None:
        if self._process is None:
            return

        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)

        self._process = None

    def _restart_gui(self) -> None:
        self.close()

        if not self.launcher_script.exists():
            raise RuntimeError(f"Flex GUI launcher not found: {self.launcher_script}")

        gui_python = _resolve_gui_python()
        cmd = [
            gui_python,
            str(self.launcher_script),
            "--port",
            self.port,
            "--baud",
            str(self.baud),
            "--wm-settings",
            str(self.wm_settings_path),
            "--auto-connect",
        ]

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )

        self._process = subprocess.Popen(
            cmd,
            cwd=str(self.launcher_script.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        time.sleep(1.5)


def _resolve_gui_python() -> str:
    executable = Path(sys.executable)
    pythonw_name = "pythonw.exe" if os.name == "nt" else executable.name
    pythonw_path = executable.with_name(pythonw_name)

    if pythonw_path.exists():
        return str(pythonw_path)

    return sys.executable
