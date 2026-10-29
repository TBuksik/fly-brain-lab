# Closed loop with the brain in one long run() + network_operation (scripts/closed_loop_netop.py)

Hook at the start of each 15 ms window: DNa02 counts of the previous window -> smoothing -> action -> 150 body
steps; then pose -> theta / distance (arrival -> net.stop()); then LC10 Poisson rates. Same operation order
and seeds as scripts/closed_loop_sweep.py; compared with docs/closed-loop-sweep-g0.82.csv (gain_right 0.82).

| bearing | windows (ref.) | DN counts identical | max abs dtheta | max abs ddist | max abs daction |
|---------|----------------|---------------------|----------------|---------------|-----------------|
| +35  | 92 (92)   | 92/92   | 3.6e-15 deg | 3.6e-15 | 1.1e-16 |
| -150 | 162 (162) | 162/162 | 1.4e-14 deg | 3.6e-15 | 1.1e-16 |

- Identical up to floating-point rounding (origin of the 1e-14 differences not checked; CSV parsing is a candidate).
- net.stop() from the hook ends the run at the arrival window, as in the reference. The "episode ended early"
  branch was not exercised.
- Time per window: 301 / 303 ms; body 261 / 263 ms (87%); brain + hook overhead 41 / 40 ms; real-time ratio
  0.050x / 0.049x, versus ~0.025x with one run() per window (docs/closed-loop-sweep.md). Expectation before the
  run was ~330 ms (body ~285 ms assumed).
- Two bearings, one brain seed, one gain.
