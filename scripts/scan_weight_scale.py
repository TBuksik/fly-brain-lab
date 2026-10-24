"""Scan a global scale on the recurrent synaptic weights (syn.w); Poisson input weight unchanged.

For each scale: stimulate one ORN type on one side (left / right) for --on seconds, then keep
running --off seconds without input. Reports activity during input, activity in the last quarter
of the off period (persistence), active neurons, the matching ALPN readout and the four DNs.
Scaling is a tuning choice (labelled [SIMPLIFICATION]), not a biological measurement.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_dn_lateral import ANN, DN_IDS  # noqa: E402  (also sets up brian2 / Eon imports)

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, second, seed  # noqa: E402
from benchmark import path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scales", type=float, nargs="+", default=[1.0, 0.8, 0.6, 0.5, 0.4, 0.3])
    ap.add_argument("--orn-type", default="ORN_DA1")
    ap.add_argument("--target-prefix", default="DA1_")
    ap.add_argument("--rate", type=float, default=20.0)
    ap.add_argument("--on", type=float, default=0.5)
    ap.add_argument("--off", type=float, default=0.5)
    ap.add_argument("--trials", type=int, default=2)
    ap.add_argument("--out", default="docs/weight-scale-scan.csv")
    args = ap.parse_args()

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    n = len(df_comp)
    base_w = np.array(syn.w_[:])  # unitless (volt) copy of the original weights

    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[
        ["root_id", "super_class", "cell_class", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    ann = ann[ann["root_id"].isin(i_of.keys())]

    def idx_of(df, side):
        return np.array([i_of[int(r)] for r in df.loc[df["side"] == side, "root_id"]], dtype=int)

    orn = ann[(ann["cell_type"] == args.orn_type) & ann["side"].isin(["left", "right"])]
    left, right = idx_of(orn, "left"), idx_of(orn, "right")
    tgt = ann[(ann["cell_class"] == "ALPN") & ann["cell_type"].astype(str).str.startswith(args.target_prefix)
              & ann["side"].isin(["left", "right"])]
    tgt_idx = {s: idx_of(tgt, s) for s in ["left", "right"]}
    print(f"{args.orn_type}: {len(left)} left / {len(right)} right; readout ALPN "
          f"{len(tgt_idx['left'])} left / {len(tgt_idx['right'])} right", flush=True)

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
    seed(1)

    on_ms = args.on * 1000.0
    late_from = on_ms + 0.5 * args.off * 1000.0
    rows = []
    for scale in args.scales:
        for side in ["left", "right"]:
            for trial in range(args.trials):
                net.restore("init")
                syn.w_ = base_w * scale
                pg.rates = np.where(is_left, args.rate if side == "left" else 0.0,
                                    args.rate if side == "right" else 0.0) * Hz
                net.run(args.on * second)
                pg.rates = 0 * Hz
                net.run(args.off * second)
                t_ms = np.asarray(spk_mon.t / ms)
                idx = np.asarray(spk_mon.i)
                on = idx[t_ms < on_ms]
                c_on = np.bincount(on, minlength=n)
                row = dict(scale=scale, side=side, trial=trial,
                           on_spikes=len(on), on_active=int((c_on > 0).sum()),
                           late_spikes=int((t_ms >= late_from).sum()),
                           tgt_L=int(c_on[tgt_idx["left"]].sum()), tgt_R=int(c_on[tgt_idx["right"]].sum()))
                for name, rid in DN_IDS.items():
                    row[name] = int(c_on[i_of[rid]])
                rows.append(row)
            print(f"scale {scale:g} {side} done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    cols = [c for c in df.columns if c not in ("scale", "side", "trial")]
    print(f"\nMean per trial ({args.trials} trials; on {args.on:g} s at {args.rate:g} Hz, "
          f"then {args.off:g} s off; late = last half of the off period):")
    print(df.groupby(["scale", "side"], sort=False)[cols].mean().round(1).to_string())
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
