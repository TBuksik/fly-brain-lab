"""Whole-brain left-right asymmetry of model activity under lateralised olfactory input.

Same stimulation as measure_dn_lateral.py (all ORNs of one side, Poisson). Collects spike
counts of all neurons per condition, aggregates by (super_class, cell_type, side) using the
FlyWire v783 annotations, and reports asymmetry. Aggregate table saved outside the repo.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_dn_lateral import ANN  # noqa: E402  (also sets up brian2 / Eon imports)

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, second, seed  # noqa: E402
from benchmark import path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=30.0)
    ap.add_argument("--duration", type=float, default=0.5)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--out", default="/tmp/lr_asymmetry_by_type.csv")
    args = ap.parse_args()

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    n_neurons = len(df_comp)

    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[
        ["root_id", "super_class", "cell_class", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    orn = ann[(ann["super_class"] == "sensory") & (ann["cell_class"] == "olfactory")
              & ann["side"].isin(["left", "right"]) & ann["root_id"].isin(i_of.keys())]
    left = np.array([i_of[int(r)] for r in orn.loc[orn["side"] == "left", "root_id"]])
    right = np.array([i_of[int(r)] for r in orn.loc[orn["side"] == "right", "root_id"]])
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

    conditions = {"left": (args.rate, 0.0), "right": (0.0, args.rate), "both": (args.rate, args.rate)}
    acc = {c: np.zeros(n_neurons) for c in conditions}
    for trial in range(args.trials):
        for cname, (rl, rr) in conditions.items():
            net.restore("init")
            pg.rates = np.where(is_left, rl, rr) * Hz
            net.run(args.duration * second)
            acc[cname] += np.bincount(np.asarray(spk_mon.i), minlength=n_neurons)
        print(f"trial {trial + 1}/{args.trials} done", flush=True)

    mean = {c: acc[c] / args.trials for c in conditions}
    df = pd.DataFrame({"root_id": df_comp.index.astype("int64"), **mean})
    df = df.merge(ann[["root_id", "super_class", "cell_type", "side"]], on="root_id", how="left")
    d = df[df["side"].isin(["left", "right"]) & df["cell_type"].notna()]
    print(f"\nTotal spikes per trial, 'both' condition: "
          f"left side {d.loc[d['side'] == 'left', 'both'].sum():.0f}, "
          f"right side {d.loc[d['side'] == 'right', 'both'].sum():.0f}")

    g = (d.groupby(["super_class", "cell_type", "side"])[list(conditions)]
         .sum().unstack("side").dropna())
    bl, br = g[("both", "left")], g[("both", "right")]
    tot = bl + br
    sel = tot >= 20
    ai = ((bl - br) / tot)[sel]
    print(f"types with both sides and >=20 spikes: {int(sel.sum())} of {len(g)}")
    print(f"asymmetry index (L-R)/(L+R), 'both' condition: median {ai.median():+.3f}, "
          f"mean {ai.mean():+.3f}; share with |AI|>0.3: {(ai.abs() > 0.3).mean():.2f}; "
          f"share with AI>0 (left-heavy): {(ai > 0).mean():.2f}")

    diff = (bl - br)[sel]
    top = diff.reindex(diff.abs().sort_values(ascending=False).index).head(15)
    print("\nTop 15 types by |L-R| spikes ('both'):")
    for (sc, ct), _ in top.items():
        print(f"  {sc:>18} {ct:<14} L={bl.loc[(sc, ct)]:8.0f} R={br.loc[(sc, ct)]:8.0f}")

    lat = (g[("left", "left")] - g[("left", "right")]) - (g[("right", "left")] - g[("right", "right")])
    by = pd.DataFrame({"lat_effect": lat, "spikes_both": tot}).groupby(level="super_class").sum()
    by["lat_effect/spikes"] = by["lat_effect"] / by["spikes_both"]
    print("\nLateralisation effect by super_class "
          "(positive = ipsilateral side more active when that side is stimulated):")
    print(by.sort_values("spikes_both", ascending=False).round(2).to_string())

    g.columns = [f"{c}_{s}" for c, s in g.columns]
    g.to_csv(args.out)
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
