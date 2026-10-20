"""Measure Brian2 runtime-mode (Cython) cost of stepping the whole-brain LIF model
in short windows, as a closed brain-body loop would.

Model: Shiu et al. LIF model, built through the Eon reference repo (set EON_REPO).
Sensory input is a PoissonGroup whose rates can be changed between windows.
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

from brian2 import Hz, Network, PoissonGroup, Synapses, ms, prefs  # noqa: E402

prefs.codegen.target = "cython"  # fail loudly instead of silently falling back to numpy

from benchmark import get_experiment, path_comp, path_con  # noqa: E402
from run_brian2_cuda import create_network, default_params  # noqa: E402

MN9_LEFT = 720575940660219265


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, default=100)
    ap.add_argument("--window-ms", type=float, default=15.0)
    ap.add_argument("--experiment", default="sugar")
    args = ap.parse_args()

    params = dict(default_params)
    need = ["eqs", "eq_th", "eq_rst", "t_rfc", "t_dly", "w_syn", "f_poi"]
    missing = [k for k in need if k not in params]
    if missing:
        sys.exit(f"default_params lacks {missing}; paste lines 45-125 of code/run_brian2_cuda.py")

    exp = get_experiment(args.experiment)
    t0 = time.perf_counter()
    neu, syn, spk_mon, df_comp, _ = create_network(path_comp, path_con, params, record_spikes=True)
    i_of = {fid: i for i, fid in enumerate(df_comp.index)}
    stim = np.array([i_of[f] for f in exp["neu_exc"]])

    pg = PoissonGroup(len(stim), rates=exp["stim_rate"] * Hz)
    w_in = params["w_syn"] * params["f_poi"]
    pg_syn = Synapses(pg, neu, on_pre="v += w_in", namespace={"w_in": w_in})
    pg_syn.connect(i=np.arange(len(stim)), j=stim)
    for i in stim:
        neu[int(i)].rfc = 0 * ms
    net = Network(neu, syn, spk_mon, pg, pg_syn)
    t_build = time.perf_counter() - t0
    print(f"network build: {t_build:.1f} s")

    window = args.window_ms * ms
    switch = args.windows // 2
    times, spikes, prev = [], [], 0
    for w in range(args.windows):
        if w == switch:
            pg.rates = 0 * Hz  # live input change: stimulus off
        t = time.perf_counter()
        net.run(window)
        times.append(time.perf_counter() - t)
        n = spk_mon.num_spikes
        spikes.append(n - prev)
        prev = n

    steady = np.array(times[1:switch])
    print(f"first window (includes Cython compile): {times[0]:.1f} s")
    print(f"steady state, {len(steady)} windows of {args.window_ms:g} ms: "
          f"median {np.median(steady)*1000:.1f} ms, p95 {np.percentile(steady, 95)*1000:.1f} ms")
    print(f"realtime ratio (median): {args.window_ms/1000/np.median(steady):.3f}x")
    tail = max(1, args.windows // 4)
    print(f"spikes per window: stimulus on (windows 1-{switch-1}) mean {np.mean(spikes[1:switch]):.1f}; "
          f"stimulus off (last {tail} windows) mean {np.mean(spikes[-tail:]):.1f}")
    print(f"MN9 left spikes in total: {int(spk_mon.count[i_of[MN9_LEFT]])}")
    print(f"peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MiB")


if __name__ == "__main__":
    main()
