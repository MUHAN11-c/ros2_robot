"""A tiny policy-search experiment; standard library only, no robot connection."""
import json
import random

def rollout(gain, seed, mass=1.0, steps=120):
    rng = random.Random(seed)
    position, velocity = rng.uniform(-2.0, 2.0), 0.0
    reward = 0.0
    for _ in range(steps):
        force = max(-1.0, min(1.0, -gain * position - 0.8 * velocity))
        velocity += (force / mass - 0.1 * velocity) * 0.05
        position += velocity * 0.05
        reward -= position ** 2 + 0.01 * force ** 2
    return reward, abs(position)

def evaluate(gain, seeds, mass=1.0):
    results = [rollout(gain, seed, mass) for seed in seeds]
    return {"gain": gain, "mass": mass,
            "mean_return": sum(x[0] for x in results) / len(results),
            "mean_final_error": sum(x[1] for x in results) / len(results)}

def main():
    candidates = [evaluate(g, range(5)) for g in (0.0, 0.25, 0.5, 1.0, 2.0)]
    best = max(candidates, key=lambda item: item["mean_return"])["gain"]
    print(json.dumps({"training": candidates, "selected_gain": best,
                      "held_out": [evaluate(best, range(100, 110), mass)
                                   for mass in (0.7, 1.0, 1.5)]}, indent=2))

if __name__ == "__main__":
    main()
