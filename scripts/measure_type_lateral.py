"""Lateralised Poisson drive of one cell type (selected by cell_type prefix) and the steering DN response.

Prints the per-trial table (no averaging across ignited / non-ignited trials) and a summary over
ignited trials. Driven neurons fire 1:1 with the Poisson input (as in the other measure_* scripts).
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

IGNITION_ACTIVE = 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True, help="cell_type prefix of the driven neurons, e.g. PFL3 or LC10")
    ap.add_argument("--rates", type=float, nargs="+", default=[10.0, 30.0, 100.0])
    ap.add_argument("--duration", type=float, default=0.5)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"docs/type-lateral-{args.prefix}.csv"

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    n = len(df_comp)

    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[["root_id", "super_class", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    ann = ann[ann["root_id"].isin(i_of.keys())]
    sel = ann[ann["cell_type"].astype(str).str.startswith(args.prefix) & ann["side"].isin(["left", "right"])]
    print(f"Neurons with cell_type starting with '{args.prefix}' in the model:")
    print(sel.groupby(["super_class", "cell_type", "side"]).size().unstack(fill_value=0).to_string(), flush=True)

    def idx_of(side):
        return np.array([i_of[int(r)] for r in sel.loc[sel["side"] == side, "root_id"]], dtype=int)

    left, right = idx_of("left"), idx_of("right")
    if len(left) == 0 or len(right) == 0:
        raise SystemExit("no neurons of that type on both sides; check --prefix")
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

    rows = []
    for rate in args.rates:
        for side in ["left", "right"]:
            for trial in range(args.trials):
                net.restore("init")
                pg.rates = np.where(is_left, rate if side == "left" else 0.0,
                                    rate if side == "right" else 0.0) * Hz
                net.run(args.duration * second)
                idx = np.asarray(spk_mon.i)
                counts = np.bincount(idx, minlength=n)
                row = dict(rate=rate, side=side, trial=trial, on_spikes=len(idx),
                           on_active=int((counts > 0).sum()))
                for name, rid in DN_IDS.items():
                    row[name] = int(counts[i_of[rid]])
                rows.append(row)
            print(f"{rate:g} Hz {side} done", flush=True)

    df = pd.DataFrame(rows)
    df["ignited"] = df["on_active"] > IGNITION_ACTIVE
    df.to_csv(out, index=False)
    print(f"\nPer-trial results (ignited = > {IGNITION_ACTIVE} active neurons):")
    print(df.drop(columns=["ignited"]).to_string(index=False))

    df["DNa02_R-L"] = df["DNa02_R"] - df["DNa02_L"]
    df["DNa01_R-L"] = df["DNa01_R"] - df["DNa01_L"]
    keys = ["rate", "side"]
    cols = ["on_active", "DNa01_L", "DNa01_R", "DNa02_L", "DNa02_R", "DNa01_R-L", "DNa02_R-L"]
    runaway = df.groupby(keys, sort=False)["ignited"].sum().rename("n_runaway")
    print("\nMean over all trials (n_runaway = trials with > 1000 active neurons; a sparse, graded "
          "response can stay below this, so the threshold is not a validity criterion):")
    print(df.groupby(keys, sort=False)[cols].mean().round(1).join(runaway).to_string())
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
