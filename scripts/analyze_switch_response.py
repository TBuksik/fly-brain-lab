"""Offline analysis of docs/switch-response-*.csv: sign-decoding accuracy vs integration length and
per-trial latencies. No simulation. Protocol must match measure_switch_response.py."""
import argparse

import numpy as np
import pandas as pd

PROTOCOL = [(0, 0.0, 0.0), (150, 30.0, 10.0), (450, 10.0, 30.0), (750, 30.0, 10.0), (1050, 0.0, 0.0)]


def first_at_least(series, t0, thr=1):
    s = series[series.index >= t0]
    hit = s[s >= thr]
    return None if hit.empty else float(hit.index[0] - t0)


def first_zero_run(series, t0, run=2):
    s = series[series.index >= t0]
    v = s.to_numpy()
    for i in range(len(v) - run + 1):
        if (v[i:i + run] == 0).all():
            return float(s.index[i] - t0)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="docs/switch-response-LC10.csv")
    ap.add_argument("--skip", type=int, default=2, help="windows skipped after each switch")
    ap.add_argument("--ks", type=int, nargs="+", default=[1, 2, 3, 4, 6, 8])
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df["diff"] = df["DNa02_R"] - df["DNa02_L"]
    win = float(np.diff(np.sort(df["t_ms"].unique()))[0])
    end_ms = float(df["t_ms"].max() + win)
    phases = []
    for k, (start, rl, rr) in enumerate(PROTOCOL):
        end = PROTOCOL[k + 1][0] if k + 1 < len(PROTOCOL) else end_ms
        if rl != rr:
            phases.append((start, end, "R" if rr > rl else "L"))

    print(f"window {win:g} ms; phases with a stronger side: {phases}; skipping {args.skip} windows after each switch")
    rows = []
    for k in args.ks:
        for truth_side in ["L", "R"]:
            truth = 1 if truth_side == "R" else -1
            correct = tie = wrong = 0
            sums = []
            for start, end, side in phases:
                if side != truth_side:
                    continue
                for _, g in df.groupby("trial"):
                    g = g.sort_values("t_ms")
                    x = g[(g["t_ms"] >= start + args.skip * win) & (g["t_ms"] < end)]["diff"].to_numpy()
                    for b in range(len(x) // k):
                        sm = x[b * k:(b + 1) * k].sum()
                        sums.append(sm)
                        s_ = np.sign(sm)
                        correct += int(s_ == truth)
                        tie += int(s_ == 0)
                        wrong += int(s_ == -truth)
            n = correct + tie + wrong
            rows.append(dict(k_windows=k, length_ms=k * win, stronger_side=truth_side, blocks=n,
                             correct=round(correct / n, 2), tie=round(tie / n, 2), wrong=round(wrong / n, 2),
                             mean_sum=round(float(np.mean(sums)), 2)))
    print("\nSign of the summed DNa02 (R-L) over k windows vs the truly stronger-driven side:")
    print(pd.DataFrame(rows).to_string(index=False))

    print("\nPer-trial latencies (ms after the switch; windows of 15 ms; None = not observed):")
    events = [(150, "DNa02_L", None, "from silence to (30,10)"), (450, "DNa02_R", "DNa02_L", "(30,10) -> (10,30)"),
              (750, "DNa02_L", "DNa02_R", "(10,30) -> (30,10)")]
    for start, new, old, label in events:
        for trial, g in df.groupby("trial"):
            s = g.sort_values("t_ms").set_index("t_ms")
            on = first_at_least(s[new], start)
            off = first_zero_run(s[old], start) if old else None
            print(f"  {label:<26} trial {trial}: first {new} spike at +{on}"
                  + (f", {old} silent (2 windows) from +{off}" if old else ""))
    stop = PROTOCOL[-1][0]
    for trial, g in df.groupby("trial"):
        s = g.sort_values("t_ms").set_index("t_ms")
        both = s["DNa02_L"] + s["DNa02_R"]
        print(f"  input off at {stop} ms, trial {trial}: both DNa02 silent (2 windows) from +{first_zero_run(both, stop)}")


if __name__ == "__main__":
    main()
