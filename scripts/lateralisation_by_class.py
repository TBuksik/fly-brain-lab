"""Where is lateralisation lost? Reads the per-type table written by map_lr_asymmetry.py.

Columns are <stimulated side>_<neuron side>: left_left = left-ORN stimulation, left-side neurons.
lat_index = ((ll - lr) - (rl - rr)) / (ll + lr + rl + rr); contra/ipsi = (lr + rl) / (ll + rr).
"""
import argparse
import os

import pandas as pd

COLS = ["left_left", "left_right", "right_left", "right_right"]
ANN = os.path.expanduser("~/refs/flywire_annotations/supplemental_files/"
                         "Supplemental_file1_neuron_annotations.tsv")


def add_metrics(df):
    ll, lr, rl, rr = (df[c] for c in COLS)
    df = df.copy()
    df["spikes_all4"] = df[COLS].sum(axis=1)
    df["lat_index"] = ((ll - lr) - (rl - rr)) / df["spikes_all4"].where(df["spikes_all4"] > 0)
    df["contra/ipsi"] = (lr + rl) / (ll + rr).where((ll + rr) > 0)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="/tmp/lr_asymmetry_by_type.csv")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    g = pd.read_csv(args.table, index_col=[0, 1])
    ann = pd.read_csv(ANN, sep="\t", low_memory=False)
    cls = (ann.dropna(subset=["cell_type"]).groupby("cell_type")["cell_class"]
           .agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else "unclassified"))
    g["cell_class"] = g.index.get_level_values("cell_type").map(cls).fillna("unclassified")
    g = g.reset_index()

    by = add_metrics(g.groupby("cell_class")[COLS].sum())
    by["n_types"] = g.groupby("cell_class").size()
    print("By cell_class (>= 200 spikes):")
    print(by[by["spikes_all4"] >= 200].sort_values("spikes_all4", ascending=False)
          [["spikes_all4", "lat_index", "contra/ipsi", "n_types"]].round(3).to_string())

    for c in ["olfactory", "ALPN", "ALLN"]:
        sub = add_metrics(g[g["cell_class"] == c].set_index("cell_type")[COLS])
        print(f"\nTop {args.top} {c} types by spikes:")
        print(sub.sort_values("spikes_all4", ascending=False).head(args.top)
              [COLS + ["lat_index", "contra/ipsi"]].round(2).to_string())

    for c in ["ALLN", "ALPN"]:
        print(f"\nPredicted neurotransmitter (annotation top_nt) of {c} neurons:")
        print(ann.loc[ann["cell_class"] == c, "top_nt"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
