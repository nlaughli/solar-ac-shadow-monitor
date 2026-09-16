"""Home Assistant add-on entry point for the shadow monitor.

The Supervisor injects a short-lived token and proxies Core at
http://supervisor/core.  The monitor only makes GET /api/states requests.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from solar_ac.control import Controller, record
from solar_ac.home_assistant import fetch_states, normalize


OPTIONS_PATH = Path("/data/options.json")
LOG_DIR = Path("/data")


def load_config():
    options = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    return {
        "temperature_unit": options["temperature_unit"],
        "grid_positive": options["grid_positive"],
        "battery_positive": options["battery_positive"],
        "energy_max_age_seconds": options["energy_max_age_seconds"],
        "nest_max_age_seconds": options["nest_max_age_seconds"],
        "entities": {key: options[key] for key in ("nest", "grid", "battery", "soc", "solar", "home")},
    }, options["poll_seconds"]


def main():
    # SUPERVISOR_TOKEN is the current documented name. Older Supervisor
    # releases may still inject the predecessor name for compatibility.
    token = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")
    if not token:
        raise RuntimeError("Supervisor API token is unavailable; enable homeassistant_api in the app manifest")
    config, poll_seconds = load_config()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    controller = Controller()
    print("Solar AC Shadow Monitor started; no thermostat or battery command path is active.", flush=True)
    while True:
        now = datetime.now(timezone.utc)
        log_path = LOG_DIR / f"shadow-{now.astimezone().date().isoformat()}.jsonl"
        try:
            sample = normalize(fetch_states("http://supervisor/core", token), config, now)
            row = record(sample, controller.step(sample))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            row = {
                "timestamp": now.isoformat(), "shadow": True, "recommended_f": None,
                "alert": "TELEMETRY_FETCH_FAILED", "error_type": type(exc).__name__,
            }
            controller = Controller()
        with log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(row, allow_nan=False) + "\n")
        print(json.dumps(row, allow_nan=False), flush=True)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
