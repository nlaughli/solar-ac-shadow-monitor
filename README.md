# Solar AC Controller

Start with [Home Assistant commissioning](docs/SETUP.md), the [active-control ship criteria](docs/ACTIVE_CONTROL_SHIP_CRITERIA.md), and the [decision test specification](docs/ACTIVE_CONTROL_TEST_SPEC.md).

Read-only Python service for FranklinWH telemetry and a Nest thermostat through Home Assistant. This first version logs recommendations only: there is no thermostat command path, including for safety recommendations.

The repository now also contains an **unactivated active-control draft**. `--plan-active` logs a proposed `climate.set_temperature` command after additional actuator guards; it never sends a command. See [active-control ship criteria](docs/ACTIVE_CONTROL_SHIP_CRITERIA.md) before considering any write path.

The proposed attended-control behavior is defined in the [decision test specification](docs/ACTIVE_CONTROL_TEST_SPEC.md). It includes 30 concrete combinations of indoor temperature, weather, solar coverage, battery state, freshness, and manual holds for review before that draft is extended.

With the supplied Windows runner, use `./scripts/run-shadow.ps1 -Continuous -PlanActive` to log those proposed commands alongside normal shadow decisions. This remains a no-write mode.

## Run locally

Use Python 3.11 or later. On Windows, install the timezone database:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m solar_ac --demo --output logs/demo.jsonl
```

The demo runs four simulated hours of strong export followed by cloud/import conditions. It is a deterministic input scenario, not a house thermal or compressor simulation. JSONL logs include raw telemetry, filtered surplus, learned AC power, recommendation, decision reason, and alerts. Nest observations are recorded separately from control-safe values: `indoor_observed_f` and humidity remain in the log when unchanged, while an aged temperature still produces `TEMPERATURE_UNAVAILABLE` and blocks control.

## Connect Home Assistant

1. Install Home Assistant on the chosen always-on host. See [setup](docs/SETUP.md).
2. Add FranklinWH and Nest and verify readings against their apps.
3. Copy `controller-config.example.json` to `config.local.json`. Fill in actual entity IDs, including the Nest humidity sensor when available, and HA temperature units. Verify both power signs; placeholders deliberately prevent valid energy recommendations.
4. Set `HA_URL` and `HA_TOKEN` in the process environment. Create the long-lived token in your HA user profile; never commit or share it. Use HTTPS outside a trusted local network.
5. Run `python -m solar_ac --config config.local.json --once` and inspect the log.
6. Run the same command without `--once` to poll every 60 seconds. Keep the terminal open or supervise the process on the selected host. Stop with Ctrl+C. No background service has been installed yet.

The token may have write privileges in HA, but this adapter only makes GET requests. Logs stay local and are excluded from Git. Plan log rotation before unattended long-term deployment.

## Control behavior

Defaults are provisional constants in `solar_ac/control.py`, not commissioned settings:

- 72°F minimum and a 74–76°F preferred occupied comfort band. At 78°F while occupied, the controller recommends 76°F; safety cooling begins at 80°F with a 78°F release threshold. At 82°F the log raises an absolute-ceiling alert. During peak, an occupied home retains the 76°F target rather than being raised for economics alone.
- Los Angeles time, including DST: pre-cool 11:30–15:30; conserve 16:00–21:00; neutral otherwise. This does not switch COOL/OFF or implement the existing overnight OFF schedule.
- Ten-minute exponential smoothing; one-degree hysteresis and maximum ordinary target step; 15-minute change spacing and 20-minute pre-cooling commitment. Comfort, safety, and telemetry faults bypass holds.
- SOC below 40% suppresses pre-cooling; below 80% limits it to 74°F. Higher SOC permits 72°F with sustained surplus.
- Positive normalized grid means export; positive battery means discharge. Counterfactual surplus adds learned running AC power, subtracts battery discharge, and is capped at measured solar production.
- AC power uses the median of up to 30 stable off/on transitions, only after ten accepted cycles. Until then no AC load is added back. This conservative fallback may miss usable solar.
- Missing, non-finite, stale, or invalid telemetry disables energy optimization. Temperature is evaluated separately from energy. A failed fetch emits an alert with no recommendation and resets transient controller state.

`state` describes the current policy; `reason` explains when timing or hysteresis holds its target. Changes refer to shadow recommendations, not actual Nest commands. The learner assumes approximately one-minute samples. State and learning reset on process restart; it starts conservatively at 76°F.

## Validation before any active-control implementation

Run sunny and cloudy days and review compressor transitions, signs, data freshness, setpoint spacing, SOC behavior, and the 16:00 transition. Compare AC estimates with observed load changes; simultaneous appliance use and variable-speed equipment can bias them. Battery dispatch can change when HVAC changes, so counterfactual surplus remains a heuristic.

The software cannot guarantee an indoor ceiling. In shadow mode even safety alerts only appear in the log, and a cool setpoint cannot ensure cooling during a fault or outage. Retain a thermostat schedule appropriate for the bird and independently monitored room temperature. No alert delivery channel is installed.

Before enabling writes, implement and validate manual override handling, actual command acknowledgement/retry, mode handling, persistent command timing, independent room sensing/alerts, and outage behavior. Active control is deliberately a later phase requiring review of real shadow data.

## Project status

Implemented and locally testable: normalization, logging, control policy, filtering, holds, load learning, demo, and tests. A Home Assistant Green is now on the network. Pending: confirming onboarding and connectivity, account integrations, sign verification, live logging, multi-day validation, and active control. The Python service currently runs separately from Green.
