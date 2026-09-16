import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from solar_ac.control import Controller, Sample
from solar_ac.home_assistant import normalize

BASE = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)


def sample(minute=0, **kwargs):
    return replace(Sample(BASE+timedelta(minutes=minute), 75, 76, False, 3, 90, 0, 5, 2), **kwargs)


class ControlTests(unittest.TestCase):
    def test_sun_cloud_taper_and_spacing(self):
        c = Controller()
        targets = [c.step(sample(i, grid_export_kw=3 if i < 100 else -1))["recommended_f"] for i in range(200)]
        changes = [i for i in range(1, len(targets)) if targets[i] != targets[i-1]]
        self.assertEqual(min(targets), 72)
        self.assertEqual(targets[-1], 77)
        self.assertTrue(all(b-a >= 15 for a,b in zip(changes, changes[1:])))

    def test_safety_bypasses_commitment_and_peak(self):
        c = Controller()
        c.step(sample())
        r = c.step(sample(1, indoor_f=81, grid_export_kw=None))
        self.assertEqual((r["recommended_f"], r["state"]), (76, "SAFETY_COOL"))
        self.assertEqual(c.step(sample(2, indoor_f=79))["state"], "SAFETY_COOL")
        self.assertEqual(c.step(sample(3, indoor_f=82))["alert"], "ABSOLUTE_CEILING_REACHED")
        c = Controller()
        self.assertEqual(c.step(sample(240, indoor_f=80, occupied=False))["state"], "SAFETY_COOL")

    def test_battery_discharge_is_not_solar_surplus(self):
        c = Controller()
        c.cycles = [3.2]*10
        for i in range(60):
            r = c.step(sample(i, grid_export_kw=0, cooling=True, battery_discharge_kw=3.2, solar_kw=1))
        self.assertEqual(r["recommended_f"], 76)
        self.assertAlmostEqual(r["filtered_surplus_kw"], 0)

    def test_counterfactual_stays_stable_on_compressor_start(self):
        c = Controller()
        c.cycles = [3.2]*10
        for i in range(60):
            r = c.step(sample(i, grid_export_kw=3 if i<20 else -.2, cooling=i>=20, home_kw=2 if i<20 else 5.2))
        self.assertAlmostEqual(r["filtered_surplus_kw"], 3)
        self.assertEqual(r["recommended_f"], 72)

    def test_low_soc_and_peak(self):
        c = Controller()
        for i in range(60):
            r = c.step(sample(i, battery_soc=30))
        self.assertEqual(r["recommended_f"], 76)
        c = Controller()
        for i in range(240, 280):
            r = c.step(sample(i))
        self.assertEqual(r["recommended_f"], 76)
        self.assertEqual(r["state"], "PEAK_CONSERVE")
        c = Controller()
        for i in range(240, 280):
            r = c.step(sample(i, occupied=False))
        self.assertEqual(r["recommended_f"], 78)

    def test_invalid_and_missing_data(self):
        for bad in (None, float("nan")):
            c = Controller()
            self.assertEqual(c.step(sample(indoor_f=bad))["alert"], "TEMPERATURE_UNAVAILABLE")
            self.assertEqual(c.step(sample(1, battery_soc=bad))["state"], "TELEMETRY_FAULT")

    def test_learning_and_gap(self):
        c = Controller()
        for i in range(80):
            running = i%8 >= 4
            c.step(sample(i, cooling=running, home_kw=5.2 if running else 2))
        self.assertAlmostEqual(c.ac_kw, 3.2)
        c.step(sample(100, grid_export_kw=0))
        self.assertEqual(c.filtered, 0)
        with self.assertRaises(ValueError):
            c.step(sample(100))

    def test_sign_units_and_staleness(self):
        config = dict(temperature_unit="C", grid_positive="import", battery_positive="charge",
                      entities={k:k for k in ("nest", "grid", "battery", "soc", "home", "solar")})
        states = [dict(entity_id=k, state=str(v), last_updated=BASE.isoformat(),
                       attributes={"unit_of_measurement":"W"})
                  for k,v in (("grid", -3000), ("battery", 1000), ("home", 2000), ("solar", 6000), ("soc", 90))]
        states.append(dict(entity_id="nest", state="cool", last_updated=BASE.isoformat(),
                           attributes={"current_temperature":25, "temperature":24, "current_humidity":42, "hvac_action":"idle"}))
        s = normalize(states, config, BASE)
        self.assertEqual((s.grid_export_kw, s.battery_discharge_kw, s.indoor_f), (3, -1, 77))
        stale = normalize(states, config, BASE+timedelta(minutes=4))
        self.assertIsNone(stale.grid_export_kw)
        self.assertEqual(stale.indoor_f, 77)
        self.assertEqual(Controller().step(stale)["state"], "TELEMETRY_FAULT")

    def test_stale_nest_temperature_is_retained_for_shadow_analysis(self):
        config = dict(temperature_unit="F", grid_positive="import", battery_positive="discharge",
                      nest_max_age_seconds=1800,
                      entities={k:k for k in ("nest", "grid", "battery", "soc", "home", "solar")})
        states = [dict(entity_id=k, state=str(v), last_updated=BASE.isoformat(),
                       attributes={"unit_of_measurement":"kW"})
                  for k,v in (("grid", 0), ("battery", 0), ("home", 1), ("solar", 1), ("soc", 90))]
        states.append(dict(entity_id="nest", state="cool", last_updated=BASE.isoformat(),
                           attributes={"current_temperature":74, "temperature":76, "current_humidity":45, "hvac_action":"idle"}))
        s = normalize(states, config, BASE+timedelta(minutes=31))
        self.assertIsNone(s.indoor_f)
        self.assertEqual(s.indoor_observed_f, 74)
        self.assertEqual(s.humidity_percent, 45)
        self.assertFalse(s.indoor_temperature_fresh)
        self.assertEqual(Controller().step(s)["alert"], "TEMPERATURE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
