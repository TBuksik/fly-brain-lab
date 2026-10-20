"""Brian2 runtime mode: ONE long net.run() with a network_operation hook every window.

This is the pattern for a closed brain-body loop that avoids the per-run() overhead
(~170 ms per call) measured in measure_brian2_runtime.py. Inside the hook a body
simulator would be stepped; here it only records timing and switches the stimulus off.
"""
import argparse
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np

EON = Path(os.environ.get("EON_REPO", Path.home() / "refs" / "eon-fly-brain"))
sys.path.insert(0, str(EON / "code"))

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, network_operation, prefs  # noqa: E402

prefs.codegen.target = "cython"

from benchmark import get_experiment, path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, default=200)
    ap.add_argument("--window-ms", type=float, default=15.0)
    args = ap.parse_args()

    params = dict(default_params)
    exp = get_experiment("sugar")
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    stim = np.array([i_of[f] for f in exp["neu_exc"]])

    pg = PoissonGroup(len(stim), rates=exp["stim_rate"] * Hz)
    w_in = params["w_syn"] * params["f_poi"]
    pg_syn = Synapses(pg, neu, on_pre="v += w_in", namespace={"w_in": w_in})
    pg_syn.connect(i=np.arange(len(stim)), j=stim)
    for i in stim:
        neu[int(i)].rfc = 0 * ms

    window = args.window_ms * ms
    switch = args.windows // 2
    stamps, counts = [], []

    @network_operation(dt=window, when="start")
    def hook(t):
        k = len(stamps)
        stamps.append(time.perf_counter())
        counts.append(spk_mon.num_spikes)
        if k == switch:
            pg.rates = 0 * Hz  # live input change: stimulus off

    net = Network(neu, syn, spk_mon, pg, pg_syn, hook)
    t0 = time.perf_counter()
    net.run(args.windows * window)
    total = time.perf_counter() - t0

    dts = np.diff(stamps)  # wall time of window k = stamps[k+1] - stamps[k]
    spikes = np.diff(counts)
    on = dts[2:switch]
    print(f"hook calls: {len(stamps)} (expected {args.windows}); total run: {total:.1f} s")
    print(f"per window ({args.window_ms:g} ms), stimulus on: median {np.median(on)*1000:.1f} ms, "
          f"p95 {np.percentile(on, 95)*1000:.1f} ms")
    print(f"realtime ratio (median window): {args.window_ms/1000/np.median(on):.3f}x; "
          f"whole run: {args.windows*args.window_ms/1000/total:.3f}x")
    print(f"spikes per window: on mean {np.mean(spikes[:switch]):.1f}; "
          f"off (last quarter) mean {np.mean(spikes[-(args.windows//4):]):.1f}")
    print(f"peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MiB")


if __name__ == "__main__":
    main()
