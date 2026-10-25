"""Open-loop body step response (no brain): how heading rate follows changes of the 2-vector action.

Warm-up with [1,1], then holds: A=[0.25,1.0] (left-turn command), B=[1.0,0.65] (right-turn command),
A again, C=[1,1]. Reports heading rate (deg/s) in bins and the time to reach 63% of the change.
Deterministic (seed 0). Window = 15 ms (150 steps of 0.1 ms) as in the closed-loop plan.
"""
import argparse

import numpy as np
from flygym import Fly
from flygym.examples.locomotion import HybridTurningController

SEQ = [("A", [0.25, 1.0]), ("B", [1.0, 0.65]), ("A", [0.25, 1.0]), ("C", [1.0, 1.0])]


def heading(obs):
    o = np.asarray(obs["fly_orientation"], dtype=float)
    return float(np.arctan2(o[1], o[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warmup", type=int, default=40)
    ap.add_argument("--hold", type=int, default=60)
    ap.add_argument("--bin", type=int, default=5)
    ap.add_argument("--window-ms", type=float, default=15.0)
    args = ap.parse_args()
    win = args.window_ms

    legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
    sensors = [f"{leg}{seg}" for leg in legs
               for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]]
    fly = Fly(init_pose="stretch", control="position", contact_sensor_placements=sensors,
              enable_adhesion=True, adhesion_force=40)
    sim = HybridTurningController(fly=fly)
    obs, _ = sim.reset(seed=0)
    steps = max(1, round(win / 1000 / sim.timestep))
    print(f"timestep {sim.timestep * 1000:g} ms, {steps} steps per {win:g} ms window", flush=True)

    def run(action, n_windows, obs):
        h = [heading(obs)]
        for _ in range(n_windows):
            for _ in range(steps):
                obs, _, term, trunc, _ = sim.step(np.asarray(action, dtype=float))
                if term or trunc:
                    raise SystemExit("episode ended early")
            h.append(heading(obs))
        rates = np.diff(np.degrees(np.unwrap(np.array(h)))) / (win / 1000)
        return obs, rates

    obs, rates = run([1.0, 1.0], args.warmup, obs)
    pre = float(rates[-20:].mean())
    print(f"warm-up [1,1], {args.warmup} windows: rate in the last 20 windows {pre:.1f} deg/s", flush=True)
    bins_ms = args.bin * win
    for name, action in SEQ:
        obs, rates = run(action, args.hold, obs)
        steady = float(rates[-20:].mean())
        sm = np.convolve(rates, np.ones(3) / 3, mode="valid")
        t63 = None
        if abs(steady - pre) >= 20:
            frac = (sm - pre) / (steady - pre)
            hit = np.where(frac >= 0.63)[0]
            t63 = None if len(hit) == 0 else (hit[0] + 3) * win
        nb = len(rates) // args.bin
        binned = rates[:nb * args.bin].reshape(nb, args.bin).mean(axis=1)
        print(f"\nhold {name} {action}: rate per {bins_ms:g} ms bin (deg/s):")
        print("  " + " ".join(f"{x:7.1f}" for x in binned))
        print(f"  previous steady {pre:.1f}, steady (last 0.30 s) {steady:.1f} deg/s, "
              f"63% of the change reached after {t63 if t63 is not None else 'n/a'} ms", flush=True)
        pre = steady


if __name__ == "__main__":
    main()
