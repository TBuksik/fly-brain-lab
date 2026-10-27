"""First closed brain-body loop (prototype): bearing error of a fixed object -> LC10 Poisson drive ->
Brian2 LIF brain (one run() per 15 ms window) -> DNa02 spike counts -> action [a0, a1] -> FlyGym body.

The visual front end (object bearing -> LC10 rates) and the DN -> leg mapping are explicit
[SIMPLIFICATION]s defined in configs/brain_body_mapping.yaml. Each window: pose -> theta -> rates ->
brain window -> DN counts -> smoothing -> action -> 150 body steps of 0.1 ms.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/brain_body_mapping.yaml")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--warmup", type=int, default=40, help="body-only windows at [1,1] before each run")
    ap.add_argument("--tag", default="v1")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    vis, bmap = cfg["vision"], cfg["mapping"]
    win = float(cfg["brain"]["window_ms"])
    alpha = 1.0 - np.exp(-win / cfg["brain"]["smoothing_tau_ms"])
    lo, hi = cfg["body"]["action_range"]
    n_win = int(round(args.seconds * 1000.0 / win))

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[["root_id", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    ann = ann[ann["root_id"].isin(i_of.keys())]
    sel = ann[ann["cell_type"].astype(str).str.startswith(vis["driven_cell_type_prefix"])
              & ann["side"].isin(["left", "right"])]

    def idx_of(side):
        return np.array([i_of[int(r)] for r in sel.loc[sel["side"] == side, "root_id"]], dtype=int)

    left, right = idx_of("left"), idx_of("right")
    print(f"{vis['driven_cell_type_prefix']}: {len(left)} left / {len(right)} right neurons", flush=True)
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
    dn_l, dn_r = i_of[DN_IDS["DNa02_L"]], i_of[DN_IDS["DNa02_R"]]

    legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
    sensors = [f"{leg}{seg}" for leg in legs
               for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]]
    fly = Fly(init_pose="stretch", control="position", contact_sensor_placements=sensors,
              enable_adhesion=True, adhesion_force=40)
    sim = HybridTurningController(fly=fly)
    steps = max(1, round(win / 1000 / sim.timestep))
    print(f"{n_win} windows of {win:g} ms = {args.seconds:g} s per run; {steps} body steps per window", flush=True)

    all_rows = []
    for trial in range(args.trials):
        for b0 in vis["initial_bearings_deg"]:
            seed(1 + trial)
            net.restore("init")
            obs, _ = sim.reset(seed=0)
            for _ in range(args.warmup * steps):
                obs, _, term, trunc, _ = sim.step(np.array([1.0, 1.0]))
            p0, psi0 = pose(obs)
            obj = p0 + vis["object_distance"] * np.array([np.cos(psi0 + np.radians(b0)),
                                                            np.sin(psi0 + np.radians(b0))])
            sm_l = sm_r = 0.0
            seen = 0
            rows = []
            ended = False
            for k_win in range(n_win):
                pos, psi = pose(obs)
                d = obj - pos
                theta = wrap_deg(np.degrees(np.arctan2(d[1], d[0])) - np.degrees(psi))
                dist = float(np.hypot(d[0], d[1]))
                r_l = vis["max_rate_hz"] * float(np.clip(theta / vis["saturation_deg"], 0.0, 1.0))
                r_r = vis["max_rate_hz"] * float(np.clip(-theta / vis["saturation_deg"], 0.0, 1.0))
                pg.rates = np.where(is_left, r_l, r_r) * Hz
                t0 = time.perf_counter()
                net.run(win * ms)
                t_brain = time.perf_counter() - t0
                total = spk_mon.num_spikes
                new = np.asarray(spk_mon.i)[seen:total]
                seen = total
                c_l, c_r = int((new == dn_l).sum()), int((new == dn_r).sum())
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
                rows.append(dict(trial=trial, bearing0=b0, k=k_win, t_ms=(k_win + 1) * win,
                                 theta_deg=theta, dist=dist, rate_L=r_l, rate_R=r_r, dn_L=c_l, dn_R=c_r,
                                 a0=act[0], a1=act[1], brain_s=t_brain, body_s=t_body))
                if ended:
                    break
            r = pd.DataFrame(rows)
            all_rows.append(r)
            print(f"\n=== trial {trial}, initial bearing {b0:+g} deg, object distance {vis['object_distance']:g} "
                  f"({len(r)} windows{', EPISODE ENDED EARLY' if ended else ''}) ===", flush=True)
            r["bin"] = r["k"] // 10
            g = r.groupby("bin").agg(t_ms=("t_ms", "max"), theta=("theta_deg", "mean"), dist=("dist", "mean"),
                                     rate_L=("rate_L", "mean"), rate_R=("rate_R", "mean"),
                                     dn_L=("dn_L", "sum"), dn_R=("dn_R", "sum"),
                                     a0=("a0", "mean"), a1=("a1", "mean"))
            print(g.round(2).to_string())
            near = r[r["theta_deg"].abs() < 20]
            print(f"first window with |theta| < 20 deg: "
                  f"{near['t_ms'].iloc[0] if len(near) else 'never'} ms; "
                  f"final theta {r['theta_deg'].iloc[-1]:.1f} deg; min distance {r['dist'].min():.1f}; "
                  f"mean |theta| in the last 0.5 s {r['theta_deg'].iloc[-33:].abs().mean():.1f} deg")
            print(f"wall per window: brain {r['brain_s'].median() * 1000:.0f} ms, body {r['body_s'].median() * 1000:.0f} ms "
                  f"(medians); run {r['brain_s'].sum() + r['body_s'].sum():.0f} s for {len(r) * win / 1000:g} s of behaviour",
                  flush=True)
    out = f"docs/closed-loop-{args.tag}.csv"
    pd.concat(all_rows).drop(columns=["bin"]).to_csv(out, index=False)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
