"""Closed-loop fixation sweep over initial bearings (prototype; one net.run() per 15 ms window).

Pose -> bearing error theta of one fixed object -> LC10 Poisson rates -> Brian2 LIF brain -> DNa02 spike
counts -> smoothing -> action [a0, a1] -> FlyGym body. Same mapping as closed_loop_fixation.py
(configs/brain_body_mapping.yaml). An episode ends on arrival (distance < --stop-dist). Visual front end
and DN -> leg mapping are explicit [SIMPLIFICATION]s. theta is recorded at the start of each window,
t_ms is the time of that sample.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from flygym import Fly
from flygym.examples.locomotion import HybridTurningController

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_dn_lateral import ANN, DN_IDS  # noqa: E402  (also sets up brian2 / Eon imports)

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, seed  # noqa: E402
from benchmark import path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402


def wrap_deg(x):
    return (x + 180.0) % 360.0 - 180.0


def pose(obs):
    pos = np.asarray(obs["fly"][0], dtype=float)[:2]
    o = np.asarray(obs["fly_orientation"], dtype=float)
    return pos, float(np.arctan2(o[1], o[0]))


def build_brain(prefix):
    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[["root_id", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    ann = ann[ann["root_id"].isin(i_of.keys())]
    sel = ann[ann["cell_type"].astype(str).str.startswith(prefix) & ann["side"].isin(["left", "right"])]

    def idx_of(side):
        return np.array([i_of[int(r)] for r in sel.loc[sel["side"] == side, "root_id"]], dtype=int)

    left, right = idx_of("left"), idx_of("right")
    print(f"{prefix}: {len(left)} left / {len(right)} right neurons", flush=True)
    all_idx = np.concatenate([left, right])
    is_left = np.arange(len(all_idx)) < len(left)
    pg = PoissonGroup(len(all_idx), rates=0 * Hz)
    w_in = params["w_syn"] * params["f_poi"]
    pg_syn = Synapses(pg, neu, on_pre="v += w_in", namespace={"w_in": w_in})
    pg_syn.connect(i=np.arange(len(all_idx)), j=all_idx)
    for i in all_idx:
        neu[int(i)].rfc = 0 * ms
    net = Network(neu, syn, spk_mon, pg, pg_syn)
    net.store("init")
    return dict(net=net, pg=pg, mon=spk_mon, is_left=is_left,
                dn_l=i_of[DN_IDS["DNa02_L"]], dn_r=i_of[DN_IDS["DNa02_R"]])


def build_body():
    legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
    sensors = [f"{leg}{seg}" for leg in legs
               for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]]
    fly = Fly(init_pose="stretch", control="position", contact_sensor_placements=sensors,
              enable_adhesion=True, adhesion_force=40)
    return HybridTurningController(fly=fly)


def run_episode(brain, sim, cfg, bearing, distance, max_windows, stop_dist, warmup, rng_seed):
    vis, bmap = cfg["vision"], cfg["mapping"]
    win = float(cfg["brain"]["window_ms"])
    alpha = 1.0 - np.exp(-win / cfg["brain"]["smoothing_tau_ms"])
    lo, hi = cfg["body"]["action_range"]
    steps = max(1, round(win / 1000 / sim.timestep))
    net, pg, mon = brain["net"], brain["pg"], brain["mon"]
    seed(rng_seed)
    net.restore("init")
    obs, _ = sim.reset(seed=0)
    for _ in range(warmup * steps):
        obs, _, term, trunc, _ = sim.step(np.array([1.0, 1.0]))
    p0, psi0 = pose(obs)
    obj = p0 + distance * np.array([np.cos(psi0 + np.radians(bearing)), np.sin(psi0 + np.radians(bearing))])
    sm_l = sm_r = 0.0
    seen = 0
    rows = []
    arrived = ended = False
    for k_win in range(max_windows):
        pos, psi = pose(obs)
        vec = obj - pos
        theta = wrap_deg(np.degrees(np.arctan2(vec[1], vec[0])) - np.degrees(psi))
        dist = float(np.hypot(vec[0], vec[1]))
        if dist < stop_dist:
            arrived = True
            break
        r_l = vis["max_rate_hz"] * float(np.clip(theta / vis["saturation_deg"], 0.0, 1.0))
        r_r = vis["max_rate_hz"] * float(np.clip(-theta / vis["saturation_deg"], 0.0, 1.0))
        pg.rates = np.where(brain["is_left"], r_l, r_r) * Hz
        t0 = time.perf_counter()
        net.run(win * ms)
        t_brain = time.perf_counter() - t0
        total = mon.num_spikes
        new = np.asarray(mon.i)[seen:total]
        seen = total
        c_l, c_r = int((new == brain["dn_l"]).sum()), int((new == brain["dn_r"]).sum())
        sm_l += alpha * (c_l - sm_l)
        sm_r += alpha * (c_r - sm_r)
        act = np.array([np.clip(1.0 - bmap["gain_left"] * sm_l, lo, hi),
                        np.clip(1.0 - bmap["gain_right"] * sm_r, lo, hi)])
        t0 = time.perf_counter()
        for _ in range(steps):
            obs, _, term, trunc, _ = sim.step(act)
            if term or trunc:
                ended = True
                break
        t_body = time.perf_counter() - t0
        rows.append(dict(bearing=bearing, k=k_win, t_ms=k_win * win, theta_deg=theta, dist=dist,
                         rate_L=r_l, rate_R=r_r, dn_L=c_l, dn_R=c_r, a0=act[0], a1=act[1],
                         brain_s=t_brain, body_s=t_body))
        if ended:
            break
    return pd.DataFrame(rows), arrived, ended


def summarize(r, bearing, arrived, ended, min_dist):
    th, ds, t = r["theta_deg"].to_numpy(), r["dist"].to_numpy(), r["t_ms"].to_numpy()
    near = np.where(np.abs(th) < 20)[0]
    k20 = int(near[0]) if len(near) else None
    out = dict(bearing=bearing, windows=len(r), arrived=arrived, ended_early=ended,
               arrival_ms=float(t[-1] + 15.0) if arrived else np.nan,
               t20_ms=float(t[k20]) if k20 is not None else np.nan,
               dtheta5=float(th[5] - th[0]) if len(th) > 5 else np.nan)
    if k20 is not None:
        m = (np.arange(len(r)) >= k20) & (ds > min_dist)
        if m.sum() >= 5:
            out.update(n_after=int(m.sum()), mean_theta_after=float(th[m].mean()),
                       mean_abs_after=float(np.abs(th[m]).mean()), max_abs_after=float(np.abs(th[m]).max()))
    out.update(min_dist=float(ds.min()), wall_s=float(r["brain_s"].sum() + r["body_s"].sum()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/brain_body_mapping.yaml")
    ap.add_argument("--bearings", type=float, nargs="+", default=[25, -25, 50, -50, 90, -90, 135, -135])
    ap.add_argument("--distance", type=float, default=20.0)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--stop-dist", type=float, default=2.0)
    ap.add_argument("--metric-min-dist", type=float, default=5.0)
    ap.add_argument("--warmup", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--gain-right", type=float, default=None,
                    help="override mapping.gain_right from the YAML (calibration, [SIMPLIFICATION])")
    ap.add_argument("--out", default="docs/closed-loop-sweep.csv")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    if args.gain_right is not None:
        cfg["mapping"]["gain_right"] = args.gain_right
    print(f"gain_left {cfg['mapping']['gain_left']}, gain_right {cfg['mapping']['gain_right']}", flush=True)
    max_windows = int(round(args.seconds * 1000.0 / cfg["brain"]["window_ms"]))
    brain = build_brain(cfg["vision"]["driven_cell_type_prefix"])
    sim = build_body()
    print(f"{len(args.bearings)} episodes, <= {max_windows} windows each, object at distance {args.distance:g}",
          flush=True)

    frames, summ = [], []
    for b0 in args.bearings:
        r, arrived, ended = run_episode(brain, sim, cfg, b0, args.distance, max_windows, args.stop_dist,
                                        args.warmup, args.seed)
        frames.append(r)
        s = summarize(r, b0, arrived, ended, args.metric_min_dist)
        summ.append(s)
        print(f"bearing {b0:+.0f}: {len(r)} windows, arrived={arrived}, wall {s['wall_s']:.0f} s", flush=True)

    pd.concat(frames).to_csv(args.out, index=False)
    print(f"\nSummary (theta in deg; t20 = first sample with |theta| < 20; *_after = windows from t20 on with "
          f"distance > {args.metric_min_dist:g}; dtheta5 = theta change over the first 5 windows):")
    print(pd.DataFrame(summ).round(1).to_string(index=False))
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
