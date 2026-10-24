"""Time course of the olfactory cascade: onset order by cell class and persistence after input off.

Drives one ORN type on one side (Poisson), then switches the input off and keeps running.
Single trial. Prints spikes per time bin and, per super_class/cell_class, how many neurons
fired, when the first spikes occur, and the spikes during input-on vs input-off.
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
    ap.add_argument("--orn-type", default="ORN_DA1")
    ap.add_argument("--side", default="left", choices=["left", "right"])
    ap.add_argument("--rate", type=float, default=20.0)
    ap.add_argument("--on", type=float, default=0.5, help="seconds with input")
    ap.add_argument("--off", type=float, default=0.5, help="seconds after input is switched off")
    ap.add_argument("--bin-ms", type=float, default=50.0)
    args = ap.parse_args()

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}

    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[
        ["root_id", "super_class", "cell_class", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    ann = ann[ann["root_id"].isin(i_of.keys())]
    sel = ann[(ann["cell_type"] == args.orn_type) & (ann["side"] == args.side)]
    stim = np.array([i_of[int(r)] for r in sel["root_id"]], dtype=int)
    print(f"stimulating {len(stim)} {args.orn_type} neurons ({args.side}) at {args.rate:g} Hz "
          f"for {args.on:g} s, then {args.off:g} s without input", flush=True)

    pg = PoissonGroup(len(stim), rates=args.rate * Hz)
    w_in = params["w_syn"] * params["f_poi"]
    pg_syn = Synapses(pg, neu, on_pre="v += w_in", namespace={"w_in": w_in})
    pg_syn.connect(i=np.arange(len(stim)), j=stim)
    for i in stim:
        neu[int(i)].rfc = 0 * ms
    net = Network(neu, syn, spk_mon, pg, pg_syn)
    seed(1)
    net.run(args.on * second)
    pg.rates = 0 * Hz
    net.run(args.off * second)

    t_ms = np.asarray(spk_mon.t / ms)
    idx = np.asarray(spk_mon.i)
    on_ms = args.on * 1000.0
    end_ms = (args.on + args.off) * 1000.0
    print(f"total spikes: {len(idx)}; during input: {int((t_ms < on_ms).sum())}; "
          f"after input off: {int((t_ms >= on_ms).sum())}")

    edges = np.arange(0.0, end_ms + args.bin_ms, args.bin_ms)
    print("\nbin start (ms) | spikes | distinct neurons   [input off at %g ms]" % on_ms)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (t_ms >= a) & (t_ms < b)
        print(f"{a:14.0f} | {int(m.sum()):6d} | {len(np.unique(idx[m])):6d}")

    label_by_id = (ann["super_class"].astype(str) + "/" + ann["cell_class"].fillna("-").astype(str)
                   ).set_axis(ann["root_id"]).to_dict()
    lab = np.array([label_by_id.get(int(r), "not annotated") for r in df_comp.index])
    df = pd.DataFrame({"cls": lab[idx], "i": idx, "t": t_ms})
    first = df.groupby("i").agg(cls=("cls", "first"), t_first=("t", "min"))
    rows = []
    for cls, grp in df.groupby("cls"):
        f = first[first["cls"] == cls]["t_first"]
        rows.append(dict(cls=cls, n_neurons=int((lab == cls).sum()), n_active=len(f),
                         median_first_ms=float(f.median()), p10_first_ms=float(f.quantile(0.1)),
                         spikes_on=int((grp["t"] < on_ms).sum()), spikes_off=int((grp["t"] >= on_ms).sum())))
    tab = pd.DataFrame(rows).set_index("cls")
    tab["spikes"] = tab["spikes_on"] + tab["spikes_off"]
    print("\nTop 20 classes by spikes (median_first_ms = median first-spike time of active neurons):")
    print(tab.sort_values("spikes", ascending=False).head(20).round(1).to_string())


if __name__ == "__main__":
    main()
