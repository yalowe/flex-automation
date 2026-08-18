from __future__ import annotations

import argparse
import os
import tkinter as tk

from FlexTesterGui import FlexTesterGUI


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Flex GUI, preload WM settings, and optionally auto-connect."
    )
    parser.add_argument("--port", default="COM10", help="Port to select in the GUI")
    parser.add_argument(
        "--baud", type=int, default=115200, help="Baud to select in the GUI"
    )
    parser.add_argument(
        "--wm-settings",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "wm_settings.json"
        ),
        help="Path to wm_settings.json to load into the GUI",
    )
    parser.add_argument(
        "--auto-connect",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Automatically connect the main controller tab after launch",
    )
    args = parser.parse_args()

    root = tk.Tk()
    app = FlexTesterGUI(root)
    app._wm_settings_path = args.wm_settings
    app._load_wm_settings()

    if args.port not in list(app.port_combo.cget("values")):
        port_values = list(app.port_combo.cget("values"))
        port_values.append(args.port)
        app.port_combo["values"] = port_values

    if args.port not in list(app.port_combo_2.cget("values")):
        port_values_2 = list(app.port_combo_2.cget("values"))
        port_values_2.append(args.port)
        app.port_combo_2["values"] = port_values_2

    app.port_combo.set(args.port)
    app.baud_combo.set(str(args.baud))

    if args.auto_connect:
        root.after(300, app.toggle_connection)

    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: (app._save_wm_settings(), app._wm_csv_close(), root.destroy()),
    )
    root.mainloop()


if __name__ == "__main__":
    main()
