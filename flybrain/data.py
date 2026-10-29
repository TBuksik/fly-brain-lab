"""Locations of the input data and fixed identifiers used by the scripts.

The data files stay outside this repository (size, licences). Override the locations with the environment
variables FLYBRAIN_DATA (directory with the completeness and connectivity files) and FLYWIRE_ANN (annotation table).
"""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("FLYBRAIN_DATA", Path.home() / "refs" / "eon-fly-brain" / "data"))
PATH_COMP = DATA_DIR / "2025_Completeness_783.csv"
PATH_CON = DATA_DIR / "2025_Connectivity_783.parquet"
ANN = Path(os.environ.get(
    "FLYWIRE_ANN",
    Path.home() / "refs" / "flywire_annotations" / "supplemental_files" / "Supplemental_file1_neuron_annotations.tsv"))

# Steering descending neurons, FlyWire v783 root IDs (Rayshubskiy et al. 2025; see docs/descending-neurons.md).
DN_IDS = {
    "DNa01_L": 720575940627787609,
    "DNa01_R": 720575940644438551,
    "DNa02_L": 720575940629327659,
    "DNa02_R": 720575940604737708,
}
