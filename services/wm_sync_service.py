import subprocess
import sys
from pathlib import Path


def run_wm_sync_if_enabled(args) -> None:
    if not args.wm_sync:
        return

    script_path = Path(args.wm_sync_script)
    settings_path = Path(args.wm_sync_settings)

    if not script_path.exists():
        msg = f"WM sync script not found: {script_path}"
        if args.wm_sync_strict:
            raise RuntimeError(msg)
        print(f"Warning: {msg}")
        return

    if not settings_path.exists():
        msg = f"WM sync settings not found: {settings_path}"
        if args.wm_sync_strict:
            raise RuntimeError(msg)
        print(f"Warning: {msg}")
        return

    cmd = [
        sys.executable,
        str(script_path),
        "--port",
        args.port,
        "--baud",
        str(args.baud),
        "--settings",
        str(settings_path),
    ]

    print("Running WM sync before test run...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    if result.returncode != 0:
        msg = "WM sync failed " f"(exit_code={result.returncode})."
        if args.wm_sync_strict:
            raise RuntimeError(msg)
        print(f"Warning: {msg}")
        return

    print("WM sync completed successfully.")
