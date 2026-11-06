"""Validate a task proposal and print a dry-run; never executes ROS commands."""
import json
import math

PLACES = {"desk": (1.0, 0.5, 0.0), "dock": (0.0, 0.0, 0.0)}

def validate(raw):
    plan = json.loads(raw)
    if not isinstance(plan, list) or not 1 <= len(plan) <= 8:
        raise ValueError("plan must contain 1..8 steps")
    for step in plan:
        if not isinstance(step, dict):
            raise ValueError("step must be an object")
        skill = step.get("skill")
        allowed = {"navigate": {"skill", "place", "timeout"},
                   "inspect": {"skill", "object", "timeout"}}
        if not isinstance(skill, str) or skill not in allowed or set(step) != allowed[skill]:
            raise ValueError("unknown skill or unexpected fields")
        timeout = step["timeout"]
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError("invalid timeout")
        if skill == "navigate" and (not isinstance(step["place"], str) or step["place"] not in PLACES):
            raise ValueError("unknown place")
        if skill == "inspect" and step["object"] not in ("cup", "marker"):
            raise ValueError("unsupported object")
    return plan

def main():
    sample = '[{"skill":"navigate","place":"desk","timeout":60},{"skill":"inspect","object":"cup","timeout":10}]'
    for index, step in enumerate(validate(sample), 1):
        print("DRY_RUN", index, step)
    for bad in ('[{"skill":"shell","command":"anything","timeout":10}]',
                '[{"skill":"navigate","place":"unknown","timeout":60}]'):
        try:
            validate(bad)
        except ValueError as error:
            print("REJECTED", error)
        else:
            raise AssertionError("invalid plan accepted")

if __name__ == "__main__":
    main()
