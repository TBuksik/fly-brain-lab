"""Both sides driven at different rates: does the steering-DN output track the left-right difference?

Drives all neurons of one cell-type family (--prefix, default LC10) on each side at (rate_L, rate_R)
for --on seconds, then --off seconds without input. Reports DN spike counts during input, total
spikes in the last half of the off period (persistence) and active neurons. Full per-trial CSV.
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
    ap.add_argument("--prefix", default="LC10")
    ap.add_argument("--rates", type=float, nargs="+", default=[0.0, 10.0, 30.0, 100.0])
    ap.add_argument("--on", type=float, default=0.5)
    ap.add_argument("--off", type=float, default=0.5)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"docs/lr-grid-{args.prefix}.csv"

    params = dict(default_params)
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    n = len(df_comp)

    ann = pd.read_csv(ANN, sep="\t", low_memory=False)[["root_id", "cell_type", "side"]]
    ann["root_id"] = ann["root_id"].astype("int64")
    ann = ann[ann["root_id"].isin(i_of.keys())]
    sel = ann[ann["cell_type"].astype(str).str.startswith(args.prefix) & ann["side"].isin(["left", "right"])]

    def idx_of(side):
        return np.array([i_of[int(r)] for r in sel.loc[sel["side"] == side, "root_id"]], dtype=int)

    left, right = idx_of("left"), idx_of("right")
    print(f"{args.prefix}: {len(left)} left / {len(right)} right neurons", flush=True)
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

    on_ms = args.on * 1000.0
    late_from = on_ms + 0.5 * args.off * 1000.0
    rows = []
    for rl in args.rates:
        for rr in args.rates:
            for trial in range(args.trials):
                net.restore("init")
                pg.rates = np.where(is_left, rl, rr) * Hz
                net.run(args.on * second)
                pg.rates = 0 * Hz
                net.run(args.off * second)
                t_ms = np.asarray(spk_mon.t / ms)
                idx = np.asarray(spk_mon.i)
                c_on = np.bincount(idx[t_ms < on_ms], minlength=n)
                row = dict(rate_L=rl, rate_R=rr, trial=trial, on_spikes=int((t_ms < on_ms).sum()),
                           on_active=int((c_on > 0).sum()), late_spikes=int((t_ms >= late_from).sum()))
                for name, rid in DN_IDS.items():
                    row[name] = int(c_on[i_of[rid]])
                rows.append(row)
            print(f"L {rl:g} Hz, R {rr:g} Hz done", flush=True)

    df = pd.DataFrame(rows)
    df["DNa02_R-L"] = df["DNa02_R"] - df["DNa02_L"]
    df["DNa01_R-L"] = df["DNa01_R"] - df["DNa01_L"]
    df["drive_diff"] = df["rate_R"] - df["rate_L"]
    df.to_csv(out, index=False)

    for col, title in [("DNa02_R-L", "DNa02 R-L (mean spikes per input window)"),
                       ("DNa01_R-L", "DNa01 R-L"), ("on_active", "active neurons during input"),
                       ("late_spikes", "spikes in the last half of the off period (persistence)")]:
        print(f"\n{title}; rows = rate_L, columns = rate_R:")
        print(df.pivot_table(index="rate_L", columns="rate_R", values=col, aggfunc="mean").round(1).to_string())

    for col in ["DNa02_R-L", "DNa01_R-L"]:
        r = np.corrcoef(df["drive_diff"], df[col])[0, 1]
        slope, icpt = np.polyfit(df["drive_diff"], df[col], 1)
        print(f"\n{col} vs (rate_R - rate_L): Pearson r = {r:.3f}, slope = {slope:.3f} spikes/Hz, "
              f"intercept = {icpt:.2f}")
    diag = df[df["rate_L"] == df["rate_R"]].groupby("rate_L")[["DNa02_R-L", "DNa01_R-L"]].mean().round(1)
    print("\nEqual input on both sides (bias), mean R-L by rate:")
    print(diag.to_string())
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
