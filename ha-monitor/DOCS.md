# Solar AC Shadow Monitor

This add-on moves the existing read-only monitor to the always-on Home Assistant Green. It reads Core state through the internal Supervisor proxy and does not need a Home Assistant long-lived token.

## What it does

- Polls the same Nest and FranklinWH entities every 60 seconds by default.
- Writes daily JSONL logs to the add-on's private configuration directory, visible in backups.
- Emits the same records to the add-on log.
- Never calls `climate.set_temperature`, changes Nest mode, or controls FranklinWH.

## Install

1. In Home Assistant, go to **Settings → Apps → App store**.
2. Open the repository menu and add this repository URL: `https://github.com/nlaughli/solar-ac-shadow-monitor`.
3. Select **Solar AC Shadow Monitor**, install it, review the entity IDs in Configuration, and start it.
4. Enable **Start on boot** and inspect the log for one valid row.

Replace every `REPLACE_ME` entity ID before starting the add-on. Use **Developer tools → States** to find the Nest climate entity and the instantaneous grid, battery, SOC, solar, and home-power entities. Verify the grid and battery sign conventions against the energy system's own application.

## Rollback

Stop or uninstall the app. Home Assistant, Nest, and FranklinWH retain their existing configuration because the monitor has no command path.
