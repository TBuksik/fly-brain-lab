import os
import pandas as pd

ann = pd.read_csv(os.path.expanduser("~/refs/flywire_annotations/supplemental_files/Supplemental_file1_neuron_annotations.tsv"),
                  sep="\t", low_memory=False)
ann["root_id"] = ann["root_id"].astype("int64")
comp = pd.read_csv(os.path.expanduser("~/refs/eon-fly-brain/data/2025_Completeness_783.csv"), index_col=0)
ann = ann[ann["root_id"].isin(set(comp.index.astype("int64")))]

kc = ann[ann["cell_type"].astype(str).str.startswith("KC")]
print("Kenyon cells in model by type and side:")
print(kc.groupby(["cell_type", "side"]).size().unstack(fill_value=0).to_string())

orn = ann[(ann["super_class"] == "sensory") & (ann["cell_class"] == "olfactory")
          & ann["side"].isin(["left", "right"])]
con = pd.read_parquet(os.path.expanduser("~/refs/eon-fly-brain/data/2025_Connectivity_783.parquet"),
                      columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
tgt = ann.set_index("root_id")[["super_class", "cell_class", "cell_type", "side"]]
for src_side in ["left", "right"]:
    ids = set(orn.loc[orn["side"] == src_side, "root_id"])
    sub = con[con["Presynaptic_ID"].isin(ids)].join(tgt, on="Postsynaptic_ID")
    tot = sub["Connectivity"].sum()
    print(f"\n=== Output synapses of {src_side} ORNs: total {tot} ===")
    print("by target side (share):")
    print((sub.groupby("side", dropna=False)["Connectivity"].sum() / tot).round(3).to_string())
    print("by target cell_class and side (synapses, top 8 classes):")
    t = sub.groupby(["cell_class", "side"])["Connectivity"].sum().unstack(fill_value=0)
    t["total"] = t.sum(axis=1)
    print(t.sort_values("total", ascending=False).head(8).to_string())
