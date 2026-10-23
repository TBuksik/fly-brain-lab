"""Measure the turning response of the FlyGym body (no brain, no rendering).

Each 2-vector action is run from a fixed-seed reset for --duration seconds.
Heading is the angle of obs["fly_orientation"] in the xy plane, sampled every
window (15 ms by default) and unwrapped, so turns beyond 180 degrees are kept.
"""
import argparse
import csv
import time

import numpy as np
from flygym import Fly
from flygym.examples.locomotion import HybridTurningController


def heading(obs):
    o = np.asarray(obs["fly_orientation"], dtype=float)
    return float(np.arctan2(o[1], o[0]))


def position_xy(obs):
    return np.asarray(obs["fly"][0], dtype=float)[:2]


def run_action(sim, action, steps_per_window, n_windows):
    """Run one action from a fresh reset; return per-window time, heading, position."""
    obs, _ = sim.reset(seed=0)
    times, heads, poss = [0.0], [heading(obs)], [position_xy(obs)]
    dt = sim.timestep
    finished = False
    for w in range(n_windows):
        for _ in range(steps_per_window):
            obs, _, terminated, truncated, _ = sim.step(action)
            if terminated or truncated:
                finished = True
                break
        times.append((w + 1) * steps_per_window * dt)
        heads.append(heading(obs))
        poss.append(position_xy(obs))
        if finished:
            break
    return np.array(times), np.unwrap(np.array(heads)), np.array(poss), finished


def summarize(times, heads_unwrapped, poss, settle_s=0.5):
    i = int(np.searchsorted(times, settle_s))
    total_deg = np.degrees(heads_unwrapped[-1] - heads_unwrapped[0])
    rate_deg_s = np.degrees(heads_unwrapped[-1] - heads_unwrapped[i]) / (times[-1] - times[i])
    disp = float(np.linalg.norm(poss[-1] - poss[0]))
    return total_deg, rate_deg_s, disp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=1.5, help="seconds per action")
    ap.add_argument("--window-ms", type=float, default=15.0)
    ap.add_argument("--out", default="docs/turning-curve.csv")
    args = ap.parse_args()

    legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
    sensors = [f"{leg}{seg}" for leg in legs
               for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]]
    fly = Fly(init_pose="stretch", control="position", contact_sensor_placements=sensors,
              enable_adhesion=True, adhesion_force=40)
    sim = HybridTurningController(fly=fly)
    sim.reset(seed=0)

    steps_per_window = max(1, round(args.window_ms / 1000 / sim.timestep))
    n_windows = round(args.duration / (args.window_ms / 1000))
    print(f"timestep {sim.timestep*1000:g} ms, {steps_per_window} steps/window, "
          f"{n_windows} windows = {args.duration:g} s per action", flush=True)

    xs = [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
    actions = [[1.0, x] for x in xs] + [[x, 1.0] for x in xs[1:]]
    actions += [[1.0, 1.0], [1.0, 0.2]]  # repeats: determinism / reset-state check
    labels = ["grid"] * (len(actions) - 2) + ["repeat", "repeat"]

    print(f"{'a0':>5} {'a1':>5} {'tag':>7} {'turn_total_deg':>15} "
          f"{'rate_deg_s(0.5-end)':>20} {'displacement':>13} {'early':>6} {'wall_s':>7}", flush=True)
    rows = []
    for action, tag in zip(actions, labels):
        t0 = time.perf_counter()
        times, heads, poss, finished = run_action(
            sim, np.array(action, dtype=float), steps_per_window, n_windows)
        total, rate, disp = summarize(times, heads, poss)
        wall = time.perf_counter() - t0
        rows.append([action[0], action[1], tag, round(total, 2), round(rate, 2),
                     round(disp, 3), int(finished), round(wall, 1)])
        print(f"{action[0]:5.1f} {action[1]:5.1f} {tag:>7} {total:15.1f} "
              f"{rate:20.1f} {disp:13.3f} {int(finished):6d} {wall:7.1f}", flush=True)

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["a0", "a1", "tag", "turn_total_deg", "rate_deg_s_after_0.5s",
                    "displacement_xy", "terminated_early", "wall_s"])
        w.writerows(rows)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
