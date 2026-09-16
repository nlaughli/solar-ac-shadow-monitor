# Active-control decision test specification

This is the reviewable behavior contract for the first attended release. It describes what the controller *would* do only after every item in `ACTIVE_CONTROL_SHIP_CRITERIA.md` is complete. Current software remains read-only and records recommendations only.

## Scope and terms

All cases use a thermostat confirmed in `cool` mode and a normal fallback target of 76°F, unless the case says otherwise. “Set” means one attended `climate.set_temperature` command followed by readback; “hold” means send no command and leave the Nest schedule or existing setpoint alone.

The controller must receive fresh room temperature, thermostat state, energy telemetry, and weather. A fresh Nest observation is no older than 30 minutes; the dedicated bird-room sensor becomes the safety temperature source before unattended operation.

`Solar cover` is the estimated fraction of the incremental AC demand supplied by surplus solar after household load and battery discharge are accounted for. It is not simply the solar-production percentage. The current data suggests a roughly 4.1 kW AC increment, but that estimate is provisional until ten clean cycles have been reviewed.

The proposed policy uses these commissioning values:

- Safety response: 80°F; absolute alert: 82°F.
- Occupied comfort band: 74–76°F; normal fallback: 76°F.
- Attended-command range: 72–78°F. The controller must not raise an occupied
  home's target above 76°F for economic reasons alone.
- Pre-cooling window: 11:30 AM–3:30 PM Pacific; peak conserve window: 4–9 PM.
- Battery reserve: low below 40% SOC; preferred for pre-cooling at or above 80% SOC.
- A forecast high at or below 78°F vetoes discretionary pre-cooling.

The 50% figure below is intentionally a decision boundary for review: it means that when solar cover is below 50%, the controller should not lower the target for economics alone. Comfort and safety overrides still apply.

Peak economics are pursued by capturing surplus solar in the pre-cooling
window, then allowing the home to coast within the 74–76°F comfort band. A
high peak tariff is not a reason to make an occupied home less comfortable.

## Decision cases

| # | Indoor / occupancy | Weather and solar condition | Battery | Expected action | Why |
| --- | --- | --- | --- | --- | --- |
| 1 | 80°F, occupied | 85°F outside; solar cover 30% | 30% SOC | Set 76°F immediately; alert safety cooling. | Safety overrides economics. This is the example of expensive AC that still must run. |
| 2 | 82°F, occupied | 95°F outside; no solar | 15% SOC | Set 76°F immediately; send absolute-ceiling alert. | Protect occupants and bird; operator attention is required. |
| 3 | 80°F, unoccupied | 83°F outside; solar cover 0% | 25% SOC | Set 76°F immediately; alert safety cooling. | Safety applies whether occupied or not. |
| 4 | 79°F, occupied | 84°F outside; solar cover 40% | 35% SOC | Set 76°F. | Occupied-comfort override. |
| 5 | 78°F, occupied | Forecast high 75°F; 70°F outside | 70% SOC | Set or retain 76°F; do not pre-cool below it. | Comfort response is allowed; mild-day veto blocks discretionary cooling. |
| 6 | 78°F, unoccupied | Forecast high 84°F; solar cover 20% | 35% SOC | Hold 76°F; alert only if temperature continues toward 80°F. | No occupied comfort response yet; conserve the reserve. |
| 7 | 77°F, occupied | 86°F outside; solar cover 45% | 30% SOC | Hold 76°F. | The normal target already offers cooling; do not pre-cool. |
| 8 | 76°F, occupied | 86°F outside; solar cover 45% | 30% SOC | Hold 76°F. | Low battery and low solar cover veto a discretionary lower target. |
| 9 | 75°F, occupied, 12:30 PM | Forecast high 92°F; 90°F outside; solar cover 100% | 95% SOC | Set 74°F. | Good pre-cooling case: hot day, surplus solar, and full battery. |
| 10 | 74°F, occupied, 1:30 PM | Forecast high 96°F; solar cover 130% | 98% SOC | Set 73°F, if 15-minute interval permits. | Pre-cool conservatively while plenty of excess solar remains. |
| 11 | 73°F, occupied, 2:30 PM | Forecast high 95°F; solar cover 150% | 100% SOC | Set 72°F, then commit for 20 minutes. | Lower bound is reached only under the strongest surplus case. |
| 12 | 72°F, occupied, 2:45 PM | Forecast high 95°F; solar cover 150% | 100% SOC | Hold 72°F; never command lower. | Hard commissioned floor. |
| 13 | 75°F, occupied, 12:30 PM | Forecast high 77°F; solar cover 150% | 100% SOC | Hold 76°F. | Mild-day forecast veto. |
| 14 | 75°F, occupied, 12:30 PM | Forecast unavailable; solar cover 150% | 100% SOC | Hold 76°F and log `forecast_unavailable`. | Missing forecast suppresses pre-cooling. |
| 15 | 75°F, occupied, 12:30 PM | Forecast high 90°F; cloud cover rapidly increasing; solar cover fell from 120% to 40% | 85% SOC | Hold the current target; do not lower further. | Filtered surplus must be sustained, not a momentary spike. |
| 16 | 75°F, occupied, 12:30 PM | Forecast high 91°F; solar cover 55% | 85% SOC | Hold 76°F. | Below the proposed 60% sustained-entry threshold; this threshold is a review decision. |
| 17 | 75°F, occupied, 12:30 PM | Forecast high 91°F; solar cover 80% sustained for 10 minutes | 85% SOC | Set 75°F. | First discretionary step under a credible surplus. |
| 18 | 75°F, occupied, 12:30 PM | Forecast high 91°F; solar cover 120% sustained for 10 minutes | 60% SOC | Set 74°F at most. | Mid-range SOC caps pre-cooling at 74°F. |
| 19 | 75°F, occupied, 12:30 PM | Forecast high 91°F; solar cover 120% sustained for 10 minutes | 39% SOC | Hold 76°F. | Low SOC protects battery reserve even with solar present. |
| 20 | 76°F, occupied, 3:20 PM | Forecast high 93°F; solar cover 130% | 95% SOC | Set 75°F at most; do not begin a deeper cycle. | The pre-cooling window is about to end, so limit the commitment. |
| 21 | 75°F, occupied, 4:05 PM | 90°F outside; solar cover 110% | 95% SOC | Set or return to 76°F, subject to no command more often than hourly. | Start peak conservation while retaining the preferred comfort band. |
| 22 | 79°F, occupied, 4:05 PM | 90°F outside; solar cover 20% | 30% SOC | Set 76°F. | Occupied comfort overrides peak conservation. |
| 23 | 80°F, occupied, 5:30 PM | 92°F outside; solar cover 0% | 20% SOC | Set 76°F; alert safety cooling. | Safety overrides peak conservation. |
| 24 | 76°F, occupied, 8:30 PM | 84°F outside; solar cover 0% | 35% SOC | Hold 76°F; do not raise it to avoid grid imports. | Preserve comfort while the battery absorbs the remaining peak exposure. |
| 25 | 76°F, occupied, 9:05 PM | 79°F outside; no solar | 35% SOC | Return toward 76°F only if Nest schedule has not already done so. | After peak, restore the normal fallback without fighting the schedule. |
| 26 | 74°F, occupied | Outdoor 68°F; user declares windows open | Any SOC | Hold; no lower target and no automatic re-engagement. | Natural ventilation is a hard manual hold. Nest does not reliably detect open windows. |
| 27 | 79°F, occupied | Outdoor 68°F; user declares windows open | Any SOC | Notify operator; do not override the ventilation hold automatically. | The operator decides whether to close windows or request cooling. |
| 28 | Any | Any; room sensor older than 30 minutes or invalid | Any SOC | Hold; disable writes; alert telemetry fault. | Cooling safety cannot be assessed from stale data. |
| 29 | 75°F, occupied | Forecast high 92°F; solar cover 120% | 90% SOC | Hold for four hours after an unacknowledged manual Nest setpoint change. | The occupant owns the thermostat after an override. |
| 30 | 75°F, occupied | Forecast high 92°F; solar cover 120% | 90% SOC | Hold after failed command readback or three telemetry faults; require operator reset. | Circuit breaker prevents repeated or invisible commands. |

## Assertions for the future automated suite

Implement each table row as a deterministic fixture with a timestamp, fresh sensor observations, forecast input, energy values, previous controller state, and expected result. Tests should assert:

1. planned target or `hold` result;
2. decision reason and alert, when applicable;
3. no plan when a hold, veto, stale reading, manual override, or circuit breaker applies;
4. one command maximum per hour in the first attended release, except a safety response; and
5. successful post-command readback before any next discretionary command.

The implementation must record every input used for a decision, including the forecast timestamp and high, outdoor temperature, solar-cover estimate, SOC, manual-hold state, and the exact veto or override reason. That makes a future command auditable against this specification.

## Decisions to settle before coding

- Confirm the 50% no-pre-cooling threshold and the 60% sustained-entry threshold, or replace both with an electricity-price-aware calculation.
- Decide the peak behavior while unoccupied: retain the current 78°F ceiling,
  or use a lower unoccupied target.
- Choose the outdoor temperature and forecast provider, and the forecast horizon used for the daily-high veto.
- Choose a room-sensor location for the bird and a humidity threshold that should override conservation.
- Decide whether natural-ventilation hold expires automatically, and if so, after what explicit user-visible interval.
- Confirm that the controller should defer to Nest schedules whenever a target already matches the desired result, rather than sending redundant commands.
