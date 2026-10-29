"""Brain-only equivalence check: one net.run() per 15 ms window vs one long run() with a network_operation
hook that sets the Poisson rates at the start of every window. Same protocol (LC10 left/right rates), same
seed; compares the full spike trains and the wall time per window. No body."""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closed_loop_sweep import build_brain  # noqa: E402  (also sets up brian2 / Eon imports)

from brian2 import Hz, ms, network_operation, seed  # noqa: E402

PROTOCOL = [(0, 0.0, 0.0), (150, 30.0, 10.0), (450, 10.0, 30.0), (750, 30.0, 10.0), (1050, 0.0, 0.0)]


def rates_for_window(k, win):
    cur = PROTOCOL[0]
    for p in PROTOCOL:
        if k * win >= p[0]:
            cur = p
    return cur[1], cur[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/brain_body_mapping.yaml")
    ap.add_argument("--windows", type=int, default=80)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    win = float(cfg["brain"]["window_ms"])
    rates = [rates_for_window(k, win) for k in range(args.windows)]
    brain = build_brain(cfg["vision"]["driven_cell_type_prefix"])
    net, pg, mon, is_left = brain["net"], brain["pg"], brain["mon"], brain["is_left"]

    def set_rates(rl, rr):
        pg.rates = np.where(is_left, rl, rr) * Hz

    def collect():
        return np.asarray(mon.i).copy(), np.asarray(mon.t / ms).copy()

    def chunked():
        seed(args.seed)
        net.restore("init")
        times = []
        for rl, rr in rates:
            set_rates(rl, rr)
            t0 = time.perf_counter()
            net.run(win * ms)
            times.append(time.perf_counter() - t0)
        return collect(), times

    print("warm-up (code generation)...", flush=True)
    seed(args.seed)
    net.restore("init")
    set_rates(30.0, 10.0)
    net.run(3 * win * ms)

    (ia, ta), times_a = chunked()
    print(f"per-window run(): {len(ia)} spikes; median {np.median(times_a) * 1000:.0f} ms per window, "
          f"total {sum(times_a):.1f} s", flush=True)

    state = {"k": 0}

    @network_operation(dt=win * ms, when="start")
    def hook(t):
        k = state["k"]
        if k < len(rates):
            set_rates(*rates[k])
        state["k"] = k + 1

    net.restore("init")
    net.add(hook)
    net.store("init_hook")
    state["k"] = 0
    seed(args.seed)
    net.run(3 * win * ms)  # warm-up for the new network
    net.restore("init_hook")
    state["k"] = 0
    seed(args.seed)
    t0 = time.perf_counter()
    net.run(args.windows * win * ms)
    total_b = time.perf_counter() - t0
    ib, tb = collect()
    print(f"single run() + hook: {len(ib)} spikes; {total_b / args.windows * 1000:.0f} ms per window, "
          f"total {total_b:.1f} s; hook calls {state['k']} (expected {args.windows})", flush=True)

    same_len = len(ia) == len(ib)
    same_i = same_len and np.array_equal(ia, ib)
    max_dt = float(np.max(np.abs(ta - tb))) if same_len and len(ta) else float("nan")
    print(f"\nspike trains: same length {same_len}; identical neuron indices {same_i}; max |t difference| {max_dt:g} ms")
    if not same_i:
        edges = np.arange(0, args.windows + 1) * win
        ca = np.histogram(ta, edges)[0]
        cb = np.histogram(tb, edges)[0]
        d = np.abs(ca - cb)
        print(f"windows with different total spike count: {int((d > 0).sum())} of {args.windows}; "
              f"max difference {int(d.max())}; mean total per window A {ca.mean():.0f}, B {cb.mean():.0f}")
        dn = [("DNa02_L", brain["dn_l"]), ("DNa02_R", brain["dn_r"])]
        for name, idx in dn:
            ra = np.histogram(ta[ia == idx], edges)[0]
            rb = np.histogram(tb[ib == idx], edges)[0]
            print(f"  {name}: total A {ra.sum()}, B {rb.sum()}")
    print(f"\nspeed-up per window: {np.median(times_a) / (total_b / args.windows):.1f}x")


if __name__ == "__main__":
    main()
