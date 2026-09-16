import argparse
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .control import Controller, Sample, record
from .home_assistant import fetch_states, normalize
from .active_control import plan_record, plan_setpoint_change


def main():
    parser = argparse.ArgumentParser(description="Solar AC shadow controller (no thermostat writes)")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--plan-active", action="store_true",
                        help="Log a proposed active-control command; never sends a command")
    parser.add_argument("--output", default="logs/shadow.jsonl")
    args = parser.parse_args()
    controller = Controller()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not args.demo:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        token = os.environ["HA_TOKEN"]
        url = os.environ["HA_URL"]
    with path.open("a", encoding="utf-8") as log:
        for minute in range(240) if args.demo else iter(int, 1):
            try:
                if args.demo:
                    now = datetime(2026, 9, 8, 18, 30, tzinfo=timezone.utc)+timedelta(minutes=minute)
                    s = Sample(now, 75, 76, False, 3 if minute < 120 else -.7, 90, 0, 5 if minute < 120 else 1, 2)
                else:
                    s = normalize(fetch_states(url, token), config, datetime.now(timezone.utc))
                decision = controller.step(s)
                row = record(s, decision)
                if args.plan_active:
                    entity = config["entities"]["nest"] if not args.demo else "climate.demo"
                    row["active_control_plan"] = plan_record(plan_setpoint_change(s, decision, entity))
            except (OSError, ValueError, KeyError, TypeError):
                row = {"timestamp": datetime.now(timezone.utc).isoformat(), "shadow": True,
                       "alert": "TELEMETRY_FETCH_FAILED", "recommended_f": None}
                controller = Controller()
            line = json.dumps(row, allow_nan=False)
            log.write(line+"\n")
            log.flush()
            print(line, flush=True)
            if args.once:
                break
            if not args.demo:
                time.sleep(60)


if __name__ == "__main__":
    main()
