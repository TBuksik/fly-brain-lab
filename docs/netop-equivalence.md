# One run() per window vs one long run() with a network_operation hook (scripts/check_netop_equivalence.py)

Brain only (no body), LC10 left/right protocol of docs/switch-response.md (80 windows of 15 ms, rates set at
the start of each window), brain seed 1. Per-window run(): rates set between calls; hook mode: one run() of
80 windows with a network_operation(dt = 15 ms, when = "start") that sets the Poisson rates.

- Spike trains identical: 21 892 spikes in both modes, same neuron indices, max time difference 0 ms.
- Hook called 80 times (expected 80).
- Time per window: 241 ms (median, per-window run()) vs 42 ms (hook mode); total 20.0 s vs 3.4 s; 5.8x.
  Earlier measurement of the hook pattern: 37 ms per window (docs/stage0-benchmarks.md).
- Not covered: rates computed from body pose, body stepping inside the hook, other seeds.
- Expected closed-loop window: ~42 ms brain + ~285 ms body = ~330 ms (~0.045x real time), not yet measured.
