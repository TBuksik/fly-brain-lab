"""Slow regression test: the own core on the full network must reproduce the frozen summary of the reference
implementation's spike train (count, active neurons, SHA-256 of neuron indices and of spike times in 0.1 ms steps).

Needs the FlyWire v783 data of the reference repo and the annotation table (about 3 GB RAM). Run: pytest -m slow
The summary can change with a different Brian2 version or random number generator; a failure then means
"investigate", not necessarily a bug.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "data" / "golden_lc10_30_10.json"
EON = Path(os.environ.get("EON_REPO", Path.home() / "refs" / "eon-fly-brain"))
ANN = Path(os.environ.get("FLYWIRE_ANN", Path.home() / "refs" / "flywire_annotations" / "supplemental_files"
                          / "Supplemental_file1_neuron_annotations.tsv"))
DATA_PRESENT = (EON / "data" / "2025_Connectivity_783.parquet").exists() and ANN.exists()


def summarize(i, t_ms):
    t_ms = np.asarray(t_ms, dtype=float)
    steps = np.rint(t_ms / 0.1).astype(np.int64)
    if not np.allclose(t_ms / 0.1, steps, atol=1e-6):
        raise ValueError("spike times are not multiples of 0.1 ms")
    idx = np.asarray(i).astype(np.int64)
    return dict(n_spikes=int(len(idx)), n_active=int(len(np.unique(idx))),
                sha256_indices=hashlib.sha256(idx.tobytes()).hexdigest(),
                sha256_time_steps=hashlib.sha256(steps.tobytes()).hexdigest())


@pytest.mark.slow
@pytest.mark.skipif(not DATA_PRESENT, reason="FlyWire data or annotation table not found")
def test_full_network_matches_frozen_reference_summary():
    golden = json.loads(GOLDEN.read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "check_own_core.py"), "--impl", "own"],
                   check=True, cwd=ROOT)
    d = np.load("/tmp/spikes_own.npz")
    assert summarize(d["i"], d["t"]) == golden["summary"]
