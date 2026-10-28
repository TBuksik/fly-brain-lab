"""Offline summary of docs/closed-loop-sweep.csv (no simulation).

Per bearing: theta / distance every N windows, convergence time (first run of consecutive windows with
abs(theta) < 20), approach-phase error statistics (distance 5-12), DNa02 activity and closing speed.
"""
import argparse

import numpy as np
import pandas as pd


def first_run(mask, n):
    run = 0
    for i, m in enumerate(mask):
        run = run + 1 if m else 0
        if run >= n:
            return i - n + 1
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="docs/closed-loop-sweep.csv")
    ap.add_argument("--every", type=int, default=10, help="print every N-th window in the time tables")
    ap.add_argument("--run", type=int, default=5, help="consecutive windows with abs(theta) < 20")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    win = float(df.groupby("bearing")["t_ms"].diff().dropna().iloc[0])
    order = list(dict.fromkeys(df["bearing"]))
    sub = df[df["k"] % args.every == 0]
    for col, nd, title in [("theta_deg", 0, "theta (deg)"), ("dist", 1, "distance (FlyGym units)")]:
        print(f"\n{title} every {args.every * win:g} ms; columns = initial bearing (blank = episode ended):")
        print(sub.pivot(index="t_ms", columns="bearing", values=col)[order].round(nd).to_string())

    rows = []
    for b in order:
        g = df[df["bearing"] == b].sort_values("k")
        th, ds, t = g["theta_deg"].to_numpy(), g["dist"].to_numpy(), g["t_ms"].to_numpy()
        k0 = first_run(np.abs(th) < 20, args.run)
        app = (ds > 5) & (ds < 12)
        closing = (ds[:-1] - ds[1:]) / (win / 1000)
        ok = np.abs(th[:-1]) < 30
        rows.append(dict(bearing=b, windows=len(g),
                         t_conv_ms=float(t[k0]) if k0 is not None else np.nan,
                         n_5_12=int(app.sum()),
                         theta_mean_5_12=float(th[app].mean()) if app.sum() else np.nan,
                         theta_sd_5_12=float(th[app].std()) if app.sum() > 1 else np.nan,
                         dnL_per_win=g["dn_L"].mean(), dnR_per_win=g["dn_R"].mean(),
                         frac_win_with_dn=((g["dn_L"] + g["dn_R"]) > 0).mean(),
                         closing_speed=float(np.median(closing[ok])) if ok.sum() else np.nan,
                         final_dist=float(ds[-1]), final_theta=float(th[-1])))
    print(f"\nPer-episode summary (t_conv = first of {args.run} consecutive windows with abs(theta) < 20; "
          f"*_5_12 = windows with distance 5-12; closing_speed = median distance decrease per second "
          f"while abs(theta) < 30):")
    print(pd.DataFrame(rows).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
