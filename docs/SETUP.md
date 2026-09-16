# Home Assistant commissioning

## Host

A Home Assistant Green is now on the household network. Confirm its URL and complete initial onboarding before adding integrations. The Python shadow controller currently runs separately and reads Green's REST API; it has not been packaged as a Green add-on. No HA subscription is needed for local REST access.

## FranklinWH

The [richo Home Assistant integration](https://github.com/richo/homeassistant-franklinwh) is unofficial and cloud dependent. Its README documents HACS installation, YAML username/password/gateway ID configuration, a default 30-second update interval, and instantaneous grid, battery, solar, home power and SOC entities. Use `secrets.yaml` for the Franklin password. Do not enable `tolerate_stale_data` for control use. Do not configure battery switches or relays for this project.

After installation, record actual entity IDs in `config.local.json`. Use instantaneous W/kW entities, not cumulative kWh import/export counters. With the app showing grid import, confirm the grid sensor sign; repeat under export. Check charging and discharging signs against the app. Internally export and battery discharge are positive. Confirm approximate balance: solar + battery discharge = home + grid export.

HA `last_reported` (or `last_updated` fallback) is checked for freshness. A cloud integration can republish old source values with fresh HA timestamps; these checks cannot establish upstream freshness. Verify failure behavior and source timestamps before active control. The chosen adapter's aPower 2/aGate firmware compatibility and cloud rate limits remain unverified on this installation.

Local Modbus options now exist in community projects, including [franklinwh-modbus](https://github.com/david2069/franklinwh-modbus). Availability depends on the gateway/firmware and has not been tested here. The controller consumes HA entities so the underlying adapter can change without rewriting policy.

## Nest

Follow the official [HA Nest setup guide](https://www.home-assistant.io/integrations/nest) for Google Device Access, Google Cloud credentials, authorization, and integration setup. Complete account authentication directly. Confirm `current_temperature`, `temperature`, `hvac_action`, and thermostat mode in HA Developer Tools. Match `temperature_unit` to HA's configured units.

Do not issue a test setpoint command during shadow commissioning. The separate Nest room probe is not used by this adapter. Choose an independent room sensor for bird-room monitoring before relying on automated protection.

## Tariff and API references

The sample policy uses a configurable household peak window and a 11:30–15:30 pre-cooling window. Review both against the applicable tariff and household comfort requirements before use; this prototype does not calculate utility prices.

The adapter uses [HA REST GET /api/states](https://developers.home-assistant.io/docs/api/rest/) with a bearer token. It does not publish recommendation entities into HA; JSONL is the initial inspection interface.
