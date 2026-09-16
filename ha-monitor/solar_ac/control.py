"""Pure, stateful controller. Power is kW; positive grid = export,
positive battery = discharge. Temperatures are Fahrenheit.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from statistics import median
from math import isfinite, exp
from zoneinfo import ZoneInfo


@dataclass
class Sample:
    timestamp: datetime
    indoor_f: float | None
    setpoint_f: float | None
    cooling: bool | None
    grid_export_kw: float | None
    battery_soc: float | None
    battery_discharge_kw: float | None
    solar_kw: float | None
    home_kw: float | None
    mode: str = "cool"
    occupied: bool = True
    # Observation fields are retained for shadow analysis even after a value is
    # too old to use for control. `indoor_f` remains the control-safe value.
    indoor_observed_f: float | None = None
    indoor_temperature_age_seconds: float | None = None
    indoor_temperature_fresh: bool = False
    humidity_percent: float | None = None
    humidity_age_seconds: float | None = None
    humidity_fresh: bool = False


class Controller:
    def __init__(self):
        self.previous = None
        self.filtered = None
        self.target = 76.0
        self.changed = None
        self.commit_until = None
        self.safety = False
        self.cycles = []
        self.off_loads = []
        self.on_loads = []
        self.baseline = None

    @property
    def ac_kw(self):
        return median(self.cycles) if len(self.cycles) >= 10 else None

    def learn(self, s):
        # Learn only stable off/on windows. Concurrent household loads can still
        # confound this heuristic; confidence requires review against real data.
        if s.cooling is False:
            self.off_loads = (self.off_loads + [s.home_kw])[-5:]
            self.on_loads = []
            self.baseline = None
        elif s.cooling is True:
            if self.previous and self.previous.cooling is False:
                if len(self.off_loads) >= 3 and max(self.off_loads)-min(self.off_loads) < .3:
                    self.baseline = median(self.off_loads)
                self.off_loads = []
            self.on_loads = (self.on_loads + [s.home_kw])[-4:]
            if len(self.on_loads) == 3 and self.baseline is not None:
                delta = median(self.on_loads) - self.baseline
                if .5 <= delta <= 8 and max(self.on_loads)-min(self.on_loads) < .4:
                    self.cycles = (self.cycles + [delta])[-30:]

    def step(self, s):
        if s.timestamp.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        dt = (s.timestamp-self.previous.timestamp).total_seconds() if self.previous else 0
        if self.previous and dt <= 0:
            raise ValueError("Samples must be strictly chronological")
        if dt > 180:
            self.filtered = None
            self.off_loads = []
            self.on_loads = []
            self.baseline = None
        temp_ok = s.indoor_f is not None and isfinite(s.indoor_f) and 32 <= s.indoor_f <= 120
        values = [s.grid_export_kw, s.battery_soc, s.battery_discharge_kw, s.solar_kw, s.home_kw]
        energy_ok = all(v is not None and isfinite(v) for v in values)
        energy_ok = energy_ok and 0 <= s.battery_soc <= 100 and 0 <= s.solar_kw <= 10 and 0 <= s.home_kw <= 50
        energy_ok = energy_ok and s.cooling is not None
        reason = ""
        if energy_ok:
            if dt <= 180:
                self.learn(s)
            # Remove battery-supported power: zero grid import alone does not
            # mean the HVAC is running on solar. Cap estimate by actual solar.
            surplus = min(s.solar_kw, s.grid_export_kw + ((self.ac_kw or 0) if s.cooling else 0)
                          - max(0, s.battery_discharge_kw))
            alpha = 1-exp(-dt/600) if self.filtered is not None else 1
            self.filtered = surplus if self.filtered is None else self.filtered + alpha*(surplus-self.filtered)
        else:
            self.filtered = None
            self.off_loads = []
            self.on_loads = []
            self.baseline = None
        local = s.timestamp.astimezone(ZoneInfo("America/Los_Angeles"))
        hour = local.hour + local.minute/60
        urgent = False
        if not temp_ok:
            desired, state, reason = 76., "TELEMETRY_FAULT", "Indoor temperature unavailable; safety cannot be assessed"
            urgent = True
        else:
            self.safety = s.indoor_f >= 80 or (self.safety and s.indoor_f > 78)
            if self.safety:
                desired, state, reason = 76., "SAFETY_COOL", "Safety cooling required; bypass timing limits"
                urgent = True
            elif s.occupied and s.indoor_f >= 78:
                desired, state, reason = 76., "NORMAL_COOL", "Occupied comfort override"
                urgent = True
            elif not energy_ok:
                desired, state, reason = 76., "TELEMETRY_FAULT", "Energy telemetry missing or invalid"
                urgent = True
            elif 16 <= hour < 21:
                if s.occupied:
                    desired, state, reason = 76., "PEAK_CONSERVE", "Peak window; retain occupied comfort"
                else:
                    desired, state, reason = 78., "PEAK_CONSERVE", "Peak window while unoccupied"
            elif 11.5 <= hour < 15.5:
                desired = 76 - 4*max(0, min(1, (self.filtered-.25)/2.25))
                if s.battery_soc < 40:
                    desired = max(76., desired)
                elif s.battery_soc < 80:
                    desired = max(74., desired)
                if self.filtered < -.5:
                    desired = 77.
                state = "SOLAR_PRECOOL" if desired < 76 else "NORMAL_COOL"
                reason = "Filtered solar surplus and battery reserve"
            else:
                desired, state, reason = 76., "NORMAL_COOL", "Outside pre-cooling window"
        desired = max(72., min(78., round(desired*2)/2))
        if not urgent:
            if self.changed and s.timestamp-self.changed < timedelta(minutes=15):
                desired, reason = self.target, "Minimum recommendation interval"
            elif self.commit_until and s.timestamp < self.commit_until and desired > self.target and state != "PEAK_CONSERVE":
                desired, reason = self.target, "Pre-cooling commitment"
            elif abs(desired-self.target) < 1:
                desired, reason = self.target, "Temperature hysteresis"
            else:
                desired = self.target + max(-1, min(1, desired-self.target))
        if desired != self.target:
            if desired < self.target and desired < 76 and not urgent:
                self.commit_until = s.timestamp + timedelta(minutes=20)
            self.changed = s.timestamp
            self.target = desired
        self.previous = s
        alert = None
        if not temp_ok:
            alert = "TEMPERATURE_UNAVAILABLE"
        elif s.indoor_f >= 82:
            alert = "ABSOLUTE_CEILING_REACHED"
        elif self.safety:
            alert = "SAFETY_COOLING_REQUIRED"
        return dict(recommended_f=self.target, state=state, reason=reason,
                    filtered_surplus_kw=self.filtered, estimated_ac_kw=self.ac_kw,
                    clean_cycles=len(self.cycles), alert=alert,
                    mode_action_required=s.mode != "cool", shadow=True)


def record(s, decision):
    return {**asdict(s), "timestamp": s.timestamp.isoformat(), **decision}
