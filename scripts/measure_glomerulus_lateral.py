"""Sparse lateralised input: drive ONE olfactory receptor type on one side only.

Reads out the projection neurons of the matching glomerulus (left / right), the stimulated
receptors, the four steering DNs and global activity. Conditions: none / left / right / both.
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
    ap.add_argument("--orn-type", default="ORN_DA1")
    ap.add_argument("--target-prefix", default="DA1_", help="cell_type prefix of ALPN readout")
    ap.add_argument("--rate", type=float, default=100.0)
    ap.add_argument("--duration", type=float, default=0.5)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"docs/glomerulus-lateral-{args.orn_type}.csv"

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    n = len(df_comp)

    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[
        ["root_id", "super_class", "cell_class", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    ann = ann[ann["root_id"].isin(i_of.keys())]

    def idx_of(df, side):
        return np.array([i_of[int(r)] for r in df.loc[df["side"] == side, "root_id"]], dtype=int)

    orn = ann[(ann["cell_type"] == args.orn_type) & ann["side"].isin(["left", "right"])]
    left, right = idx_of(orn, "left"), idx_of(orn, "right")
    print(f"{args.orn_type}: {len(left)} left, {len(right)} right neurons", flush=True)
    if len(left) == 0 or len(right) == 0:
        raise SystemExit("no neurons of that type on both sides; check --orn-type")

    tgt = ann[(ann["cell_class"] == "ALPN") & ann["cell_type"].astype(str).str.startswith(args.target_prefix)
              & ann["side"].isin(["left", "right"])]
    tgt_idx = {s: idx_of(tgt, s) for s in ["left", "right"]}
    print(f"ALPN readout types: {sorted(tgt['cell_type'].unique())}; "
          f"{len(tgt_idx['left'])} left, {len(tgt_idx['right'])} right neurons", flush=True)

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

    conditions = {"none": (0.0, 0.0), "left": (args.rate, 0.0),
                  "right": (0.0, args.rate), "both": (args.rate, args.rate)}
    rows = []
    for trial in range(args.trials):
        for cname, (rl, rr) in conditions.items():
            net.restore("init")
            pg.rates = np.where(is_left, rl, rr) * Hz
            net.run(args.duration * second)
            idx = np.asarray(spk_mon.i)
            counts = np.bincount(idx, minlength=n)
            row = dict(condition=cname, trial=trial,
                       orn_L=int(counts[left].sum()), orn_R=int(counts[right].sum()),
                       tgt_L=int(counts[tgt_idx["left"]].sum()), tgt_R=int(counts[tgt_idx["right"]].sum()))
            for name, rid in DN_IDS.items():
                row[name] = int(counts[i_of[rid]])
            row["total_spikes"] = len(idx)
            row["n_active"] = int((counts > 0).sum())
            rows.append(row)
        print(f"trial {trial + 1}/{args.trials} done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    cols = [c for c in df.columns if c not in ("condition", "trial")]
    order = list(conditions)
    print(f"\nMean per trial ({args.trials} trials, {args.duration} s, {args.rate} Hz):")
    print(df.groupby("condition")[cols].mean().reindex(order).round(1).to_string())
    print("\nSD across trials:")
    print(df.groupby("condition")[cols].std().reindex(order).round(1).to_string())
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
