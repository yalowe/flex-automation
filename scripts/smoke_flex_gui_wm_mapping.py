from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.flex_gui_service import build_wm_settings_payload


def main() -> None:
    existing_settings = {
        "5": {"show": True, "cycle_ms": "1200"},
    }
    config_data = {
        "wm_cycle": 4000,
        "dosing_channels": {
            1: {"enabled": True, "dm_cycle": 17143},
            2: {"enabled": True, "dm_cycle": 1714},
            4: {"enabled": False, "dm_cycle": 1200},
        },
    }

    payload = build_wm_settings_payload(config_data, existing_settings)

    assert payload["1"]["cycle_ms"] == "4000", payload
    assert payload["2"]["show"] is True, payload
    assert payload["2"]["cycle_ms"] == "17143", payload
    assert payload["3"]["show"] is True, payload
    assert payload["3"]["cycle_ms"] == "1714", payload
    assert payload["4"]["show"] is False, payload
    assert payload["4"]["cycle_ms"] == "1000", payload
    assert payload["5"]["show"] is False, payload
    assert payload["5"]["cycle_ms"] == "1200", payload

    print("smoke_flex_gui_wm_mapping: PASS")


if __name__ == "__main__":
    main()
