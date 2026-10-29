"""Regression check: does the own core (flybrain.model) reproduce the reference implementation spike for spike?

Run once per implementation in separate processes (each network needs ~3 GB RAM), then compare:
  python scripts/check_own_core.py --impl eon
  python scripts/check_own_core.py --impl own
  python scripts/check_own_core.py --impl compare
Stimulus: LC10 of the left side at --rate-left, of the right side at --rate-right for --on s, then --off s
without input (Poisson input, one spike adds 68.75 mV, rfc = 0 for the driven neurons), brain seed 1.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
EON = Path(os.environ.get("EON_REPO", Path.home() / "refs" / "eon-fly-brain"))
ANN = Path(os.environ.get("FLYWIRE_ANN", Path.home() / "refs" / "flywire_annotations" / "supplemental_files"
                          / "Supplemental_file1_neuron_annotations.tsv"))
PATH_COMP = EON / "data" / "2025_Completeness_783.csv"
PATH_CON = EON / "data" / "2025_Connectivity_783.parquet"


def out_path(impl):
    return f"/tmp/spikes_{impl}.npz"


def run_impl(impl, args):
    from brian2 import Hz, Network, PoissonGroup, Synapses, mV, ms, prefs, second, seed
    prefs.codegen.target = "cython"
    t0 = time.perf_counter()
    if impl == "eon":
        sys.path.insert(0, str(EON / "code"))
        from run_brian2_cuda import create_network, default_params
        neu, syn, mon, df_comp, _ = create_network(str(PATH_COMP), str(PATH_CON), dict(default_params),
                                                   record_spikes=True)
        root_ids = df_comp.index.to_numpy(dtype=np.int64)
    else:
        from flybrain.model import build_network, load_connectome
        con = load_connectome(PATH_COMP, PATH_CON)
        print("index check passed: stored indices match the positions of the root IDs", flush=True)
        parts = build_network(con)
        neu, syn, mon, root_ids = parts.neurons, parts.synapses, parts.monitor, con.root_ids
    print(f"{impl}: network built in {time.perf_counter() - t0:.0f} s, {len(root_ids)} neurons", flush=True)

    ann = pd.read_csv(ANN, sep="\t", low_memory=False, usecols=["root_id", "cell_type", "side"])
    ann["root_id"] = ann["root_id"].astype("int64")
    position = pd.Series(np.arange(len(root_ids)), index=root_ids)
    sel = ann[ann["cell_type"].astype(str).str.startswith(args.prefix) & ann["side"].isin(["left", "right"])
              & ann["root_id"].isin(position.index)]
    left = position.loc[sel.loc[sel["side"] == "left", "root_id"]].to_numpy()
    right = position.loc[sel.loc[sel["side"] == "right", "root_id"]].to_numpy()
    idx = np.concatenate([left, right])
    is_left = np.arange(len(idx)) < len(left)
    print(f"{args.prefix}: {len(left)} left / {len(right)} right neurons", flush=True)

    pg = PoissonGroup(len(idx), rates=np.where(is_left, args.rate_left, args.rate_right) * Hz)
    pg_syn = Synapses(pg, neu, on_pre="v += w_in", namespace={"w_in": 68.75 * mV})
    pg_syn.connect(i=np.arange(len(idx)), j=idx)
    neu.rfc[idx] = 0 * ms
    net = Network(neu, syn, mon, pg, pg_syn)
    seed(1)
    t0 = time.perf_counter()
    net.run(args.on * second)
    pg.rates = 0 * Hz
    net.run(args.off * second)
    print(f"{impl}: run {time.perf_counter() - t0:.1f} s; {mon.num_spikes} spikes, "
          f"{len(np.unique(np.asarray(mon.i)))} active neurons", flush=True)
    np.savez(out_path(impl), i=np.asarray(mon.i), t=np.asarray(mon.t / ms))


def compare():
    a, b = np.load(out_path("eon")), np.load(out_path("own"))
    print(f"spikes: reference {len(a['i'])}, own {len(b['i'])}")
    same_len = len(a["i"]) == len(b["i"])
    same_i = same_len and np.array_equal(a["i"], b["i"])
    max_dt = float(np.max(np.abs(a["t"] - b["t"]))) if same_len and len(a["t"]) else float("nan")
    print(f"same length {same_len}; identical neuron indices {same_i}; max |t difference| {max_dt:g} ms")
    if not same_i:
        n = int(max(a["i"].max(), b["i"].max())) + 1
        ca, cb = np.bincount(a["i"], minlength=n), np.bincount(b["i"], minlength=n)
        print(f"neurons with different spike counts: {int((ca != cb).sum())}; "
              f"max difference {int(np.abs(ca - cb).max())}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", choices=["eon", "own", "compare"], required=True)
    ap.add_argument("--prefix", default="LC10")
    ap.add_argument("--rate-left", type=float, default=30.0)
    ap.add_argument("--rate-right", type=float, default=10.0)
    ap.add_argument("--on", type=float, default=0.3)
    ap.add_argument("--off", type=float, default=0.2)
    args = ap.parse_args()
    compare() if args.impl == "compare" else run_impl(args.impl, args)


if __name__ == "__main__":
    main()
