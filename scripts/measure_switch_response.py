"""Time course of the steering-DN response when the left/right drive is switched (15 ms windows).

Protocol (start_ms, rate_L, rate_R): silent, (30,10), (10,30), (30,10), silent. All neurons of one
cell-type family (--prefix, default LC10) per side are driven by Poisson input. The network runs in
consecutive windows; Poisson rates are re-set when the protocol changes. Per-window DN spike counts.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_dn_lateral import ANN, DN_IDS  # noqa: E402  (also sets up brian2 / Eon imports)

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, seed  # noqa: E402
from benchmark import path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402

PROTOCOL = [(0, 0.0, 0.0), (150, 30.0, 10.0), (450, 10.0, 30.0), (750, 30.0, 10.0), (1050, 0.0, 0.0)]


def rates_at(t_ms):
    cur = PROTOCOL[0]
    for p in PROTOCOL:
        if t_ms >= p[0]:
            cur = p
    return cur[1], cur[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="LC10")
    ap.add_argument("--window-ms", type=float, default=15.0)
    ap.add_argument("--total-ms", type=float, default=1200.0)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"docs/switch-response-{args.prefix}.csv"
    win = args.window_ms

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

    dn_idx = {name: i_of[rid] for name, rid in DN_IDS.items()}
    n_win = int(round(args.total_ms / win))
    rows = []
    for trial in range(args.trials):
        net.restore("init")
        seen, cur = 0, None
        for k_win in range(n_win):
            t0 = k_win * win
            rl, rr = rates_at(t0)
            if (rl, rr) != cur:
                pg.rates = np.where(is_left, rl, rr) * Hz
                cur = (rl, rr)
            net.run(win * ms)
            total = spk_mon.num_spikes
            new = np.asarray(spk_mon.i)[seen:total]
            seen = total
            counts = np.bincount(new, minlength=n)
            row = dict(trial=trial, t_ms=t0, rate_L=rl, rate_R=rr, spikes=len(new),
                       active=int((counts > 0).sum()))
            for name, i in dn_idx.items():
                row[name] = int(counts[i])
            rows.append(row)
        print(f"trial {trial + 1}/{args.trials} done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    cols = ["rate_L", "rate_R", "DNa02_L", "DNa02_R", "DNa01_L", "DNa01_R", "active", "spikes"]
    m = df.groupby("t_ms")[cols].mean().round(2)
    switches = [p[0] for p in PROTOCOL[1:]]
    show = sorted({t for s in switches for t in m.index if s - 2 * win <= t < s + 8 * win})
    print(f"\nMean over {args.trials} trials, spikes per {win:g} ms window, around each switch:")
    print(m.loc[show].to_string())

    print("\nEnd of each phase (last 7 windows), mean spikes per window:")
    for k, (start, rl, rr) in enumerate(PROTOCOL):
        end = PROTOCOL[k + 1][0] if k + 1 < len(PROTOCOL) else args.total_ms
        sub = m[(m.index >= end - 7 * win) & (m.index < end)]
        print(f"  phase {start}-{end:g} ms, L={rl:g} R={rr:g} Hz: DNa02_L {sub['DNa02_L'].mean():.2f}, "
              f"DNa02_R {sub['DNa02_R'].mean():.2f}, DNa01_L {sub['DNa01_L'].mean():.2f}, "
              f"DNa01_R {sub['DNa01_R'].mean():.2f}, active {sub['active'].mean():.0f}")

    print("\nFirst window (after the switch) in which the new winner exceeds the old one (DNa02, mean over trials):")
    for k, (start, rl, rr) in enumerate(PROTOCOL[1:], start=1):
        prev = PROTOCOL[k - 1]
        if (rl, rr) == (0.0, 0.0):
            continue
        want = "DNa02_R" if rr > rl else "DNa02_L"
        other = "DNa02_L" if want == "DNa02_R" else "DNa02_R"
        later = m[m.index >= start]
        hit = later[later[want] > later[other]]
        lat = (hit.index[0] - start) if len(hit) else None
        print(f"  switch at {start} ms to L={rl:g} R={rr:g}: {want} first above {other} at +{lat} ms"
              if lat is not None else f"  switch at {start} ms: no change of winner observed")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
