"""Do lateralised sensory inputs produce asymmetric steering-DN activity?

Stimulates all olfactory receptor neurons (ORNs) of one side (annotation soma side) with
Poisson input and counts spikes of DNa01 / DNa02 (left, right). Reuses the Brian2 model from
the Eon reference repo (Shiu et al. LIF). Conditions: none / left / right / both.
"""
import argparse
import csv
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

EON = Path(os.environ.get("EON_REPO", Path.home() / "refs" / "eon-fly-brain"))
ANN = Path(os.environ.get(
    "FLYWIRE_ANN",
    Path.home() / "refs" / "flywire_annotations" / "supplemental_files"
    / "Supplemental_file1_neuron_annotations.tsv"))
sys.path.insert(0, str(EON / "code"))

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, prefs, second, seed  # noqa: E402

prefs.codegen.target = "cython"

from benchmark import path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402

# Rayshubskiy et al. 2025 (eLife), FlyWire v783; sides match the annotation table.
DN_IDS = {
    "DNa01_L": 720575940627787609,
    "DNa01_R": 720575940644438551,
    "DNa02_L": 720575940629327659,
    "DNa02_R": 720575940604737708,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=100.0, help="Poisson rate per ORN, Hz")
    ap.add_argument("--duration", type=float, default=0.5, help="seconds per trial")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", default="docs/dn-lateral-test.csv")
    args = ap.parse_args()

    params = dict(default_params)
    t0 = time.perf_counter()
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    print(f"network built: {time.perf_counter() - t0:.0f} s, {len(df_comp)} neurons", flush=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}

    ann = pd.read_csv(ANN, sep="\t", low_memory=False)
    orn = ann[(ann["super_class"] == "sensory") & (ann["cell_class"] == "olfactory")
              & ann["side"].isin(["left", "right"])]
    orn = orn[orn["root_id"].astype("int64").isin(i_of.keys())]
    left = np.array([i_of[int(r)] for r in orn.loc[orn["side"] == "left", "root_id"]])
    right = np.array([i_of[int(r)] for r in orn.loc[orn["side"] == "right", "root_id"]])
    print(f"ORNs in model: left {len(left)}, right {len(right)} (side=na skipped)", flush=True)

    all_idx = np.concatenate([left, right])
    is_left = np.arange(len(all_idx)) < len(left)

    pg = PoissonGroup(len(all_idx), rates=0 * Hz)
    w_in = params["w_syn"] * params["f_poi"]
    pg_syn = Synapses(pg, neu, on_pre="v += w_in", namespace={"w_in": w_in})
    pg_syn.connect(i=np.arange(len(all_idx)), j=all_idx)
    for i in all_idx:  # copied from measure_brian2_netop.py (Poisson-driven neurons)
        neu[int(i)].rfc = 0 * ms

    net = Network(neu, syn, spk_mon, pg, pg_syn)
    net.store("init")
    seed(1)

    conditions = {"none": (0.0, 0.0), "left": (args.rate, 0.0),
                  "right": (0.0, args.rate), "both": (args.rate, args.rate)}
    rows = []
    hdr = ["condition", "trial"] + list(DN_IDS) + ["total_spikes", "n_active", "wall_s"]
    print(f"{hdr[0]:>9} {hdr[1]:>5} " + " ".join(f"{h:>8}" for h in hdr[2:]), flush=True)
    for trial in range(args.trials):
        for name, (rl, rr) in conditions.items():
            net.restore("init")  # restore also resets pg.rates, so set rates afterwards
            pg.rates = np.where(is_left, rl, rr) * Hz
            t1 = time.perf_counter()
            net.run(args.duration * second)
            wall = time.perf_counter() - t1
            idx = np.asarray(spk_mon.i)
            counts = np.bincount(idx, minlength=len(df_comp))
            dn = [int(counts[i_of[v]]) for v in DN_IDS.values()]
            row = [name, trial] + dn + [len(idx), int((counts > 0).sum()), round(wall, 1)]
            rows.append(row)
            print(f"{name:>9} {trial:5d} " + " ".join(f"{x:8}" for x in row[2:]), flush=True)

    df = pd.DataFrame(rows, columns=hdr)
    print("\nMean DN spike counts per trial (duration %.2f s):" % args.duration)
    m = df.groupby("condition")[list(DN_IDS)].mean().reindex(list(conditions))
    m["DNa01_R-L"] = m["DNa01_R"] - m["DNa01_L"]
    m["DNa02_R-L"] = m["DNa02_R"] - m["DNa02_L"]
    print(m.round(1).to_string())
    df.to_csv(args.out, index=False)
    print(f"saved {args.out}; peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MiB")


if __name__ == "__main__":
    main()
