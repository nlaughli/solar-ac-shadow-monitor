# Active-control ship criteria

This is a release checklist for the transition from read-only recommendations to attended Nest setpoint changes. The draft actuator is not an authorization to enable it. Normal execution remains shadow-only; `--plan-active` records a proposed command without sending one.

## Intended policy

Use discretionary solar only when the house needs cooling. A forecast high at or below 78°F is a **pre-cooling veto**: keep the neutral target unless humidity, the 74–76°F occupied comfort band, or a safety limit requires cooling. A lower setpoint must never be justified by excess solar alone. Avoiding peak grid import is achieved through solar-funded pre-cooling and battery use; it must not raise an occupied home's target above 76°F for economics alone.

The initial active scope is deliberately narrow: one `climate.set_temperature` command to the Hallway Nest while it is already in COOL mode. The controller must not set HVAC mode, toggle power, change Franklin battery behavior, or touch any other device.

## Engineering completion

- [ ] Add a forecast adapter using `weather.forecast_home` and cache the daily high. If the forecast is missing or invalid, suppress pre-cooling.
- [ ] Add a manual natural-ventilation input and treat it as a hard hold on any lower setpoint.
- [ ] Add durable command state outside the process: last command, observed setpoint, command acknowledgement, and manual-override hold expiry survive restart.
- [ ] Define manual override: a Nest setpoint that differs from the last acknowledged controller command suspends optimization for at least four hours, while retaining temperature safety monitoring.
- [ ] Add bounded readback: after a command, read Nest state until the expected target appears or a timeout occurs; alert and stop further commands on timeout.
- [ ] Add a circuit breaker: three telemetry faults or one failed readback disable writes until an operator resets the controller.
- [ ] Add a dedicated bird-room temperature sensor and delivered alerts for 80°F and 82°F. Nest’s event-driven reading is insufficient as the sole safety sensor.
- [ ] Add a supervised service, restart policy, log rotation, daily heartbeat, and secret injection that does not put the HA token in a command line or repository file.
- [ ] Restrict the HA token/account to the minimum practicable permissions and document revocation.

## Shadow-data gates

- [ ] At least seven days of continuous shadow logs, including sunny, cloudy, mild, and peak-period days.
- [ ] At least ten clean, reviewed compressor on/off transitions with no concurrent large household load changes; compare inferred AC kW to Franklin data.
- [ ] Franklin instantaneous telemetry availability is at least 99% during each daytime validation window, or a more reliable local source replaces the custom cloud integration.
- [ ] Nest/room-temperature freshness is characterized. An unchanged Nest event must not be mistaken for a new measurement.
- [ ] Forecast high and observed outdoor conditions are logged. Confirm that mild-day guard proposals do not lower the 76°F neutral target.
- [ ] Every shadow decision that would produce a command is reviewed for target, reason, frequency, peak-window behavior, and manual intervention.

## Attended release procedure

1. Freeze a reviewed controller version and back up the Home Assistant configuration.
2. Enable only the command-plan log for one more attended day; compare it with the Nest state and the operator's intended actions.
3. Enable writes only during a daytime attended window. Keep targets between 72°F and 78°F and start with one change per hour.
4. Verify each command on the Nest display or Google Home, then verify Home Assistant readback before another command is permitted.
5. Test the kill switch, a manual Nest override, unavailable Franklin telemetry, unavailable room sensor, and controller restart. Each must stop writes and leave Nest on its fallback schedule.
6. Run active control for one attended week before any unattended operation.

## Rollback

Disable the active supervisor or its explicit enable flag, restore the agreed Nest schedule/target/mode, and verify it at the thermostat. Revoking the controller's HA token prevents further service calls. Preserve the JSONL and Home Assistant logs for review.
