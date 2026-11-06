"""Demonstrate timestamp/dimension/finite/rate checks for a six-joint policy."""
import math

def gate(candidate, previous, age_seconds, dt, limit=0.5):
    # These are position targets in radians, not torques or velocities.
    if len(candidate) != 6 or len(previous) != 6:
        raise ValueError("expected six joints in the agreed order")
    if not all(math.isfinite(x) for x in (*candidate, *previous, age_seconds, dt, limit)):
        raise ValueError("non-finite input")
    if dt <= 0 or limit <= 0:
        raise ValueError("invalid control interval or rate limit")
    if age_seconds < 0 or age_seconds > 0.1:
        return None  # Caller must select its independently verified stop/hold mode.
    output = []
    for target, last in zip(candidate, previous):
        bounded = max(-1.0, min(1.0, target))
        output.append(last + max(-limit * dt, min(limit * dt, bounded - last)))
    return output

def main():
    print("ACCEPTED", gate([0.5] * 6, [0.0] * 6, 0.02, 0.02))
    print("STALE", gate([0.5] * 6, [0.0] * 6, 0.3, 0.02))
    try:
        gate([float("nan")] * 6, [0.0] * 6, 0.02, 0.02)
    except ValueError as error:
        print("REJECTED", error)

if __name__ == "__main__":
    main()
