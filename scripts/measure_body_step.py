"""Measure the cost of stepping the FlyGym body headless (no brain, no rendering).

HybridTurningController takes a 2-vector action: |action[i]| sets the CPG amplitude of
the three legs on one side, the sign sets their direction. A 15 ms brain window
corresponds to window_ms / timestep physics steps (150 at the default 0.1 ms).
"""
import argparse
import resource
import time

import numpy as np
from flygym import Fly
from flygym.examples.locomotion import HybridTurningController


def position(obs):
    try:
        return np.array(obs["fly"][0], dtype=float)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, default=100)
    ap.add_argument("--window-ms", type=float, default=15.0)
    ap.add_argument("--adhesion", type=int, default=1)
    ap.add_argument("--left", type=float, default=1.0)
    ap.add_argument("--right", type=float, default=1.0)
    args = ap.parse_args()

    legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
    sensors = [f"{leg}{seg}" for leg in legs
               for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]]
    fly = Fly(init_pose="stretch", control="position", contact_sensor_placements=sensors,
              enable_adhesion=bool(args.adhesion), adhesion_force=40)
    sim = HybridTurningController(fly=fly)
    t0 = time.perf_counter()
    obs, info = sim.reset(seed=0)
    print(f"setup + reset: {time.perf_counter() - t0:.1f} s")
    print("obs keys:", list(obs.keys()) if hasattr(obs, "keys") else type(obs))

    dt = getattr(sim, "timestep", 1e-4)
    n = max(1, round(args.window_ms / 1000 / dt))
    action = np.array([args.left, args.right], dtype=float)
    print(f"timestep {dt*1000:g} ms -> {n} physics steps per {args.window_ms:g} ms window")

    def do_step():
        out = sim.step(action)
        done = len(out) == 5 and bool(out[2] or out[3])
        return out[0], done

    for _ in range(200):  # warm-up
        obs, done = do_step()
    pos0 = position(obs)

    times, finished = [], False
    for _ in range(args.windows):
        t = time.perf_counter()
        for _ in range(n):
            obs, done = do_step()
            if done:
                finished = True
                break
        times.append(time.perf_counter() - t)
        if finished:
            print("episode terminated/truncated early")
            break

    med = float(np.median(times))
    print(f"median per {args.window_ms:g} ms window: {med*1000:.1f} ms "
          f"(p95 {np.percentile(times, 95)*1000:.1f} ms), per step: {med/n*1e6:.0f} us")
    print(f"realtime ratio: {args.window_ms/1000/med:.3f}x")
    pos1 = position(obs)
    if pos0 is not None and pos1 is not None:
        print("displacement over the timed part (FlyGym units):", np.round(pos1 - pos0, 3))
    print(f"peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MiB")


if __name__ == "__main__":
    main()
