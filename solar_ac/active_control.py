"""Draft actuator boundary for the future attended active-control release.

Nothing imports or invokes ``apply_plan`` from the normal shadow runner.  This
module first makes a command plan visible in the JSONL log.  Sending a command
requires a later, separately reviewed supervisor to pass ``execute=True``.
"""
from dataclasses import asdict, dataclass
import json
from urllib.request import Request, urlopen

from .control import Sample


@dataclass(frozen=True)
class CommandPlan:
    allowed: bool
    entity_id: str
    target_f: float | None
    reason: str
    service: str = "climate.set_temperature"


def plan_setpoint_change(sample: Sample, decision: dict, thermostat_entity: str,
                         *, manual_override: bool = False) -> CommandPlan:
    """Turn a shadow recommendation into a proposed setpoint command.

    This is deliberately stricter than the recommendation engine. It refuses
    to plan a command for telemetry faults, mode uncertainty, an override, an
    unchanged target, or a target outside the commissioned 72–78°F range.
    """
    target = decision.get("recommended_f")
    if decision.get("alert") or decision.get("state") == "TELEMETRY_FAULT":
        return CommandPlan(False, thermostat_entity, None, "Telemetry or safety acknowledgement required")
    if manual_override:
        return CommandPlan(False, thermostat_entity, None, "Manual override hold is active")
    if sample.mode != "cool" or sample.cooling is None:
        return CommandPlan(False, thermostat_entity, None, "Thermostat COOL mode is not confirmed")
    if target is None or not 72 <= target <= 78:
        return CommandPlan(False, thermostat_entity, None, "Recommended target is outside commissioned bounds")
    if sample.setpoint_f is None:
        return CommandPlan(False, thermostat_entity, None, "Current thermostat setpoint is unavailable")
    if abs(target - sample.setpoint_f) < 0.25:
        return CommandPlan(False, thermostat_entity, target, "Thermostat already has the proposed target")
    return CommandPlan(True, thermostat_entity, target, "Eligible only after active-release gates pass")


def plan_record(plan: CommandPlan) -> dict:
    """JSON-safe representation used by ``--plan-active`` shadow logs."""
    return asdict(plan)


def apply_plan(url: str, token: str, plan: CommandPlan, *, execute: bool = False) -> dict:
    """Execute one already-approved plan.

    ``execute`` defaults to false so an accidental call is a no-op. This draft
    provides the narrow Home Assistant service payload only; command ownership,
    durable override state, acknowledgement polling, retries, and alerting are
    release-gate work and intentionally are not wired to the CLI.
    """
    if not plan.allowed:
        return {"sent": False, "reason": plan.reason}
    if not execute:
        return {"sent": False, "reason": "Dry run; active execution is disabled"}
    payload = json.dumps({"entity_id": plan.entity_id, "temperature": plan.target_f}).encode()
    request = Request(url.rstrip("/") + "/api/services/climate/set_temperature", data=payload,
                      headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urlopen(request, timeout=20) as response:
        response.read()
    return {"sent": True, "entity_id": plan.entity_id, "target_f": plan.target_f}
