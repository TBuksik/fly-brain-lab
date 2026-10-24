"""Where does steering-DN activity come from? Per trial, for each DN, sum over presynaptic
partners of (partner spike count x signed synapse count). Crude drive estimate, ignores
membrane dynamics. Uses the same lateralised ORN stimulation as measure_dn_lateral.py.
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_dn_lateral import ANN, DN_IDS, EON  # noqa: E402  (also sets up brian2 / Eon imports)

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, second, seed  # noqa: E402
from benchmark import path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=30.0)
    ap.add_argument("--duration", type=float, default=0.5)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--out", default="docs/dn-input-drive.csv")
    args = ap.parse_args()

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    n = len(df_comp)

    ann = pd.read_csv(ANN, sep="\t", low_memory=False).set_index("root_id")
    orn = ann[(ann["super_class"] == "sensory") & (ann["cell_class"] == "olfactory")
              & ann["side"].isin(["left", "right"])]
    orn = orn[orn.index.astype("int64").isin(i_of.keys())]
    left = np.array([i_of[int(r)] for r in orn.index[orn["side"] == "left"]])
    right = np.array([i_of[int(r)] for r in orn.index[orn["side"] == "right"]])
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

    con = pd.read_parquet(EON / "data" / "2025_Connectivity_783.parquet",
                          columns=["Presynaptic_ID", "Postsynaptic_ID", "Excitatory x Connectivity"])
    inputs = {}
    for name, rid in DN_IDS.items():
        sub = con[con["Postsynaptic_ID"] == rid]
        inputs[name] = (sub["Presynaptic_ID"].to_numpy(),
                        np.array([i_of[int(x)] for x in sub["Presynaptic_ID"]]),
                        sub["Excitatory x Connectivity"].to_numpy().astype(float))

    conditions = {"left": (args.rate, 0.0), "right": (0.0, args.rate), "both": (args.rate, args.rate)}
    rows, contrib_sum = [], {}
    for trial in range(args.trials):
        for cname, (rl, rr) in conditions.items():
            net.restore("init")
            pg.rates = np.where(is_left, rl, rr) * Hz
            net.run(args.duration * second)
            counts = np.bincount(np.asarray(spk_mon.i), minlength=n)
            for dn, (ids, idx, w) in inputs.items():
                c = counts[idx] * w
                rows.append(dict(condition=cname, trial=trial, dn=dn, dn_spikes=int(counts[i_of[DN_IDS[dn]]]),
                                 partners_active=int((counts[idx] > 0).sum()),
                                 exc_drive=float(c[c > 0].sum()), inh_drive=float(-c[c < 0].sum()),
                                 net_drive=float(c.sum())))
                if cname == "left":
                    contrib_sum.setdefault(dn, np.zeros(len(idx)))
                    contrib_sum[dn] += c
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)

    cols = ["dn_spikes", "partners_active", "exc_drive", "inh_drive", "net_drive"]
    print(f"Mean per trial ({args.trials} trials, {args.duration} s, {args.rate} Hz):")
    print(df.groupby(["condition", "dn"])[cols].mean().round(1).to_string())

    for dn in ["DNa02_L", "DNa02_R"]:
        ids, idx, w = inputs[dn]
        mean_c = contrib_sum[dn] / args.trials
        order = np.argsort(-np.abs(mean_c))[:8]
        print(f"\nTop contributors to {dn} (left-ORN condition, mean per trial):")
        for k in order:
            a = ann.loc[int(ids[k])] if int(ids[k]) in ann.index else None
            desc = f"{a['super_class']}/{a['cell_type']}/{a['side']}" if a is not None else "not annotated"
            print(f"  {int(ids[k])}  w={w[k]:>6.0f}  contrib={mean_c[k]:>8.1f}  {desc}")
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
