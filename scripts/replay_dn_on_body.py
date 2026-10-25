"""Open-loop replay: recorded steering-DN spike counts -> body actions -> FlyGym heading.

The brain is NOT running. Reads docs/switch-response-*.csv (per-window DNa02 counts), maps them with
configs/brain_body_mapping.yaml and steps the headless HybridTurningController 150 steps per window.
Reports heading change and turn rate per stimulus phase. Mapping = explicit [SIMPLIFICATION].
"""
import argparse
import time

import numpy as np
import pandas as pd
import yaml
from flygym import Fly
from flygym.examples.locomotion import HybridTurningController


def heading(obs):
    o = np.asarray(obs["fly_orientation"], dtype=float)
    return float(np.arctan2(o[1], o[0]))


def actions_from_counts(n_left, n_right, cfg):
    alpha = 1.0 - np.exp(-cfg["brain"]["window_ms"] / cfg["brain"]["smoothing_tau_ms"])
    lo, hi = cfg["body"]["action_range"]
    gl, gr = cfg["mapping"]["gain_left"], cfg["mapping"]["gain_right"]
    r_l = r_r = 0.0
    out = []
    for l, r in zip(n_left, n_right):
        r_l += alpha * (float(l) - r_l)
        r_r += alpha * (float(r) - r_r)
        out.append((float(np.clip(1.0 - gl * r_l, lo, hi)), float(np.clip(1.0 - gr * r_r, lo, hi))))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/brain_body_mapping.yaml")
    ap.add_argument("--csv", default="docs/switch-response-LC10.csv")
    ap.add_argument("--out", default="docs/replay-phases.csv")
    ap.add_argument("--warmup", type=int, default=10, help="windows of action [1,1] before the replay")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    df = pd.read_csv(args.csv)
    win = float(cfg["brain"]["window_ms"])

    legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
    sensors = [f"{leg}{seg}" for leg in legs
               for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]]
    fly = Fly(init_pose="stretch", control="position", contact_sensor_placements=sensors,
              enable_adhesion=True, adhesion_force=40)
    sim = HybridTurningController(fly=fly)
    sim.reset(seed=0)
    steps = max(1, round(win / 1000 / sim.timestep))
    print(f"timestep {sim.timestep * 1000:g} ms, {steps} steps per {win:g} ms window", flush=True)

    out_rows = []
    hdr = (f"{'trial':>5} {'start_ms':>8} {'rate_L':>6} {'rate_R':>6} {'mean_a0':>8} {'mean_a1':>8} "
           f"{'dheading_deg':>13} {'rate_deg_s':>11} {'rate_last_half':>15}")
    print(hdr, flush=True)
    for trial, g in df.groupby("trial"):
        g = g.sort_values("t_ms").reset_index(drop=True)
        acts = actions_from_counts(g["DNa02_L"], g["DNa02_R"], cfg)
        obs, _ = sim.reset(seed=0)
        for _ in range(args.warmup * steps):
            obs, _, term, trunc, _ = sim.step(np.array([1.0, 1.0]))
        h = [heading(obs)]
        stopped = False
        t0 = time.perf_counter()
        for a in acts:
            for _ in range(steps):
                obs, _, term, trunc, _ = sim.step(np.asarray(a, dtype=float))
                if term or trunc:
                    stopped = True
                    break
            h.append(heading(obs))
            if stopped:
                break
        n_done = len(h) - 1
        h = np.degrees(np.unwrap(np.array(h)))
        key = g[["rate_L", "rate_R"]]
        run_id = (key != key.shift()).any(axis=1).cumsum()
        for _, idx in g.groupby(run_id).groups.items():
            idx = [i for i in idx if i < n_done]
            if not idx:
                continue
            s, e = idx[0], idx[-1]
            m = s + len(idx) // 2
            dur = (e - s + 1) * win / 1000
            rate = (h[e + 1] - h[s]) / dur
            half = (h[e + 1] - h[m]) / max((e + 1 - m) * win / 1000, 1e-9)
            row = dict(trial=trial, start_ms=g.loc[s, "t_ms"], rate_L=g.loc[s, "rate_L"],
                       rate_R=g.loc[s, "rate_R"], mean_a0=acts[m:e + 1, 0].mean(), mean_a1=acts[m:e + 1, 1].mean(),
                       dheading_deg=h[e + 1] - h[s], rate_deg_s=rate, rate_last_half=half)
            out_rows.append(row)
            print(f"{trial:5d} {row['start_ms']:8.0f} {row['rate_L']:6.0f} {row['rate_R']:6.0f} "
                  f"{row['mean_a0']:8.2f} {row['mean_a1']:8.2f} {row['dheading_deg']:13.1f} "
                  f"{row['rate_deg_s']:11.1f} {row['rate_last_half']:15.1f}", flush=True)
        print(f"  trial {trial}: {n_done} windows, wall {time.perf_counter() - t0:.0f} s"
              + (" (episode ended early)" if stopped else ""), flush=True)
    pd.DataFrame(out_rows).to_csv(args.out, index=False)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
