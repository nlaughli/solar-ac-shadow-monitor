"""Read-only HA REST adapter. No service or thermostat write endpoints."""
import json
import math
from datetime import datetime
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlparse
from .control import Sample


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("HA redirects refused to protect authorization header")


def fetch_states(url, token):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
        raise ValueError("Use a direct Home Assistant HTTP(S) URL")
    request = Request(url.rstrip("/")+"/api/states", headers={"Authorization": "Bearer "+token})
    with build_opener(NoRedirect).open(request, timeout=20) as response:
        return json.load(response)


def normalize(states, config, now):
    entities = {s["entity_id"]: s for s in states}

    def observed(key):
        item = entities.get(config["entities"].get(key))
        if not item or item["state"] in ("unknown", "unavailable"):
            return None, None
        stamp = item.get("last_reported", item.get("last_updated"))
        try:
            delta = (now-datetime.fromisoformat(stamp)).total_seconds()
            return item, delta if delta >= -10 else None
        except (ValueError, TypeError):
            return item, None

    def entity(key, age):
        item, delta = observed(key)
        return item if delta is not None and delta <= age else None

    def number(value):
        try:
            value = float(value)
            return value if math.isfinite(value) else None
        except (TypeError, ValueError):
            return None

    def power(key):
        item = entity(key, config.get("energy_max_age_seconds", 180))
        if not item:
            return None
        value = number(item["state"])
        unit = item.get("attributes", {}).get("unit_of_measurement")
        return value / (1000 if unit == "W" else 1) if value is not None and unit in ("W", "kW") else None

    raw_climate, climate_age = observed("nest")
    climate = raw_climate if climate_age is not None and climate_age <= config.get("nest_max_age_seconds", 1800) else None
    attrs = climate.get("attributes", {}) if climate else {}
    raw_attrs = raw_climate.get("attributes", {}) if raw_climate else {}
    unit = config["temperature_unit"]
    if unit not in ("F", "C"):
        raise ValueError("temperature_unit must be F or C, matching HA")
    def temperature(key):
        value = number(attrs.get(key))
        return value*9/5+32 if value is not None and unit == "C" else value
    def raw_temperature(key):
        value = number(raw_attrs.get(key))
        return value*9/5+32 if value is not None and unit == "C" else value
    grid, battery = power("grid"), power("battery")
    if config.get("grid_positive") not in ("import", "export") or config.get("battery_positive") not in ("charge", "discharge"):
        raise ValueError("Explicit grid and battery sign conventions required")
    if grid is not None and config["grid_positive"] == "import":
        grid = -grid
    if battery is not None and config["battery_positive"] == "charge":
        battery = -battery
    soc = entity("soc", config.get("energy_max_age_seconds", 180))
    action = attrs.get("hvac_action")
    raw_humidity, humidity_age = observed("humidity")
    humidity = number(raw_humidity["state"]) if raw_humidity else number(raw_attrs.get("current_humidity"))
    if raw_humidity is None:
        humidity_age = climate_age
    humidity_fresh = humidity is not None and humidity_age is not None and humidity_age <= config.get("nest_max_age_seconds", 1800)
    return Sample(now, temperature("current_temperature"), temperature("temperature"),
                  action == "cooling" if action in ("cooling", "idle", "off") else None,
                  grid, number(soc["state"]) if soc else None, battery, power("solar"), power("home"),
                  climate["state"] if climate else "unknown",
                  indoor_observed_f=raw_temperature("current_temperature"),
                  indoor_temperature_age_seconds=climate_age,
                  indoor_temperature_fresh=climate is not None,
                  humidity_percent=humidity,
                  humidity_age_seconds=humidity_age,
                  humidity_fresh=humidity_fresh)
