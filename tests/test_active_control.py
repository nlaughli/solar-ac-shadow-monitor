import unittest
from datetime import datetime, timezone

from solar_ac.active_control import apply_plan, plan_setpoint_change
from solar_ac.control import Sample


def sample(**kwargs):
    values = dict(timestamp=datetime(2026, 9, 13, tzinfo=timezone.utc), indoor_f=75,
                  setpoint_f=76, cooling=False, grid_export_kw=1, battery_soc=90,
                  battery_discharge_kw=0, solar_kw=2, home_kw=1, mode="cool")
    values.update(kwargs)
    return Sample(**values)


class ActiveControlPlanTests(unittest.TestCase):
    entity = "climate.example_thermostat"

    def test_allows_a_safe_changed_target(self):
        plan = plan_setpoint_change(sample(), {"recommended_f": 75, "state": "NORMAL_COOL", "alert": None}, self.entity)
        self.assertTrue(plan.allowed)
        self.assertEqual(plan.target_f, 75)

    def test_blocks_faults_alerts_and_manual_override(self):
        for decision, override in (({"recommended_f": 75, "state": "TELEMETRY_FAULT", "alert": None}, False),
                                   ({"recommended_f": 75, "state": "NORMAL_COOL", "alert": "SAFETY_COOLING_REQUIRED"}, False),
                                   ({"recommended_f": 75, "state": "NORMAL_COOL", "alert": None}, True)):
            self.assertFalse(plan_setpoint_change(sample(), decision, self.entity, manual_override=override).allowed)

    def test_blocks_unconfirmed_mode_current_target_and_out_of_bounds(self):
        decision = {"recommended_f": 76, "state": "NORMAL_COOL", "alert": None}
        self.assertFalse(plan_setpoint_change(sample(), decision, self.entity).allowed)
        self.assertFalse(plan_setpoint_change(sample(mode="off"), {**decision, "recommended_f": 75}, self.entity).allowed)
        self.assertFalse(plan_setpoint_change(sample(), {**decision, "recommended_f": 70}, self.entity).allowed)

    def test_apply_is_dry_run_by_default(self):
        plan = plan_setpoint_change(sample(), {"recommended_f": 75, "state": "NORMAL_COOL", "alert": None}, self.entity)
        result = apply_plan("http://example.invalid", "never-used", plan)
        self.assertEqual(result["reason"], "Dry run; active execution is disabled")


if __name__ == "__main__":
    unittest.main()
