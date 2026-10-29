"""Closed brain-body loop with the brain in ONE long net.run() and a network_operation hook per 15 ms window.

Hook at the start of window k:
  1. (k > 0) DNa02 spike counts of window k-1 from the monitor -> smoothing -> action [a0, a1] ->
     150 body steps (the body motion of window k-1);
  2. pose -> bearing error theta and distance; arrival -> net.stop();
  3. LC10 Poisson rates for window k.
Same order as scripts/closed_loop_sweep.py (pose -> rates -> brain window -> counts -> action -> body steps), so
with the same seeds the trajectories should be identical; the script compares with a sweep CSV.
Visual front end and DN -> leg mapping are explicit [SIMPLIFICATION]s (configs/brain_body_mapping.yaml).
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closed_loop_sweep import build_body, build_brain, pose, wrap_deg  # noqa: E402

from brian2 import Hz, ms, network_operation, seed  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/brain_body_mapping.yaml")
    ap.add_argument("--bearings", type=float, nargs="+", default=[35, -150])
    ap.add_argument("--distance", type=float, default=20.0)
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--stop-dist", type=float, default=2.0)
    ap.add_argument("--warmup", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--reference", default="docs/closed-loop-sweep-g0.82.csv")
    ap.add_argument("--core", choices=["eon", "own"], default="eon")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    vis, bmap = cfg["vision"], cfg["mapping"]
    win = float(cfg["brain"]["window_ms"])
    alpha = 1.0 - np.exp(-win / cfg["brain"]["smoothing_tau_ms"])
    lo, hi = cfg["body"]["action_range"]
    max_windows = int(round(args.seconds * 1000.0 / win))
    print(f"gain_left {bmap['gain_left']}, gain_right {bmap['gain_right']}", flush=True)

    brain = build_brain(vis["driven_cell_type_prefix"], core=args.core)
    print(f"network core: {args.core}", flush=True)
    sim = build_body()
    steps = max(1, round(win / 1000 / sim.timestep))
    net, pg, mon, is_left = brain["net"], brain["pg"], brain["mon"], brain["is_left"]
    dn_l, dn_r = brain["dn_l"], brain["dn_r"]
    ep = {"active": False}

    def finish_window():
        p = ep["pending"]
        total = mon.num_spikes
        new = np.asarray(mon.i)[ep["seen"]:total]
        ep["seen"] = total
        c_l, c_r = int((new == dn_l).sum()), int((new == dn_r).sum())
        ep["sm_l"] += alpha * (c_l - ep["sm_l"])
        ep["sm_r"] += alpha * (c_r - ep["sm_r"])
        act = np.array([np.clip(1.0 - bmap["gain_left"] * ep["sm_l"], lo, hi),
                        np.clip(1.0 - bmap["gain_right"] * ep["sm_r"], lo, hi)])
        t0 = time.perf_counter()
        obs = ep["obs"]
        for _ in range(steps):
            obs, _, term, trunc, _ = sim.step(act)
            if term or trunc:
                ep["ended"] = True
                break
        ep["body_s"] += time.perf_counter() - t0
        ep["obs"] = obs
        ep["rows"].append({**p, "dn_L": c_l, "dn_R": c_r, "a0": act[0], "a1": act[1]})
        ep["pending"] = None

    @network_operation(dt=win * ms, when="start")
    def hook(t):
        if not ep["active"] or ep["stopped"]:
            return
        if ep["pending"] is not None:
            finish_window()
            if ep["ended"]:
                ep["stopped"] = True
                net.stop()
                return
        k = ep["k"]
        pos, psi = pose(ep["obs"])
        vec = ep["obj"] - pos
        theta = wrap_deg(np.degrees(np.arctan2(vec[1], vec[0])) - np.degrees(psi))
        dist = float(np.hypot(vec[0], vec[1]))
        if dist < args.stop_dist:
            ep["arrived"] = True
            ep["stopped"] = True
            net.stop()
            return
        r_l = vis["max_rate_hz"] * float(np.clip(theta / vis["saturation_deg"], 0.0, 1.0))
        r_r = vis["max_rate_hz"] * float(np.clip(-theta / vis["saturation_deg"], 0.0, 1.0))
        pg.rates = np.where(is_left, r_l, r_r) * Hz
        ep["pending"] = dict(bearing=ep["bearing"], k=k, t_ms=k * win, theta_deg=theta, dist=dist,
                             rate_L=r_l, rate_R=r_r)
        ep["k"] = k + 1

    net.restore("init")
    net.add(hook)
    net.store("init_hook")
    seed(args.seed)
    print("warm-up (code generation, hook inactive)...", flush=True)
    net.run(3 * win * ms)

    ref = pd.read_csv(args.reference)
    for b in args.bearings:
        seed(args.seed)
        net.restore("init_hook")
        obs, _ = sim.reset(seed=0)
        for _ in range(args.warmup * steps):
            obs, _, term, trunc, _ = sim.step(np.array([1.0, 1.0]))
        p0, psi0 = pose(obs)
        obj = p0 + args.distance * np.array([np.cos(psi0 + np.radians(b)), np.sin(psi0 + np.radians(b))])
        ep.update(active=True, stopped=False, ended=False, arrived=False, k=0, seen=0, sm_l=0.0, sm_r=0.0,
                  obs=obs, obj=obj, pending=None, rows=[], body_s=0.0, bearing=b)
        t0 = time.perf_counter()
        net.run(max_windows * win * ms)
        wall = time.perf_counter() - t0
        if not ep["stopped"] and ep["pending"] is not None:
            finish_window()
        ep["active"] = False

        r = pd.DataFrame(ep["rows"])
        old = ref[ref["bearing"] == b].sort_values("k").reset_index(drop=True)
        n = min(len(r), len(old))
        print(f"\n=== bearing {b:+g}: {len(r)} windows (reference {len(old)}), arrived {ep['arrived']}, "
              f"ended early {ep['ended']} ===")
        if n:
            d_th = np.abs(r["theta_deg"].to_numpy()[:n] - old["theta_deg"].to_numpy()[:n])
            d_ds = np.abs(r["dist"].to_numpy()[:n] - old["dist"].to_numpy()[:n])
            dn_same = (r["dn_L"].to_numpy()[:n] == old["dn_L"].to_numpy()[:n]) & \
                      (r["dn_R"].to_numpy()[:n] == old["dn_R"].to_numpy()[:n])
            d_a = np.maximum(np.abs(r["a0"].to_numpy()[:n] - old["a0"].to_numpy()[:n]),
                             np.abs(r["a1"].to_numpy()[:n] - old["a1"].to_numpy()[:n]))
            bad = np.where((d_th > 1e-9) | (d_ds > 1e-9) | ~dn_same | (d_a > 1e-9))[0]
            print(f"max |dtheta| {d_th.max():g} deg; max |ddist| {d_ds.max():g}; DN counts identical in "
                  f"{int(dn_same.sum())}/{n} windows; max |daction| {d_a.max():g}; "
                  f"first differing window: {int(bad[0]) if len(bad) else 'none'}")
        print(f"wall {wall:.1f} s = {wall / len(r) * 1000:.0f} ms per window; body {ep['body_s'] / len(r) * 1000:.0f} ms; "
              f"brain + hook overhead {(wall - ep['body_s']) / len(r) * 1000:.0f} ms; "
              f"real-time ratio {len(r) * win / 1000 / wall:.3f}x", flush=True)


if __name__ == "__main__":
    main()
