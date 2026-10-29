# Own network core (flybrain/model.py) vs the reference implementation (scripts/check_own_core.py)

flybrain/model.py is written from docs/model-parameters.md (equations and parameter values), not copied from the
reference code. It differs from the reference in one deliberate way: the reset statement does not contain the
reference's "w = 0" (neurons have no variable w). load_connectome verifies that the stored pre/post indices match
the positions of the root IDs in the completeness file (the earlier pipeline assumed this without checking).

Test: LC10 left 30 Hz / right 10 Hz for 0.3 s, then 0.2 s without input; Poisson input, one input spike adds
68.75 mV, rfc = 0 for the driven neurons; brain seed 1; each implementation in its own process.

- Index check passed.
- Spikes: reference 7322, own 7322; identical neuron indices; max time difference 0 ms; 1122 active neurons in both.
- Supports that "w = 0" in the reset was a no-op for this stimulus (one stimulus, one seed).
- Build time 6 s vs 1 s, run 15.8 s vs 2.0 s (own vs reference); not profiled (candidates: ID checks in the loader,
  Cython compilation of the new objects).

## Closed loop on the own core (scripts/closed_loop_netop.py --core own)

Same check as docs/closed-loop-netop.md, with flybrain.model instead of the reference network builder
(reference trajectories: docs/closed-loop-sweep-g0.82.csv).

| bearing | windows (ref.) | DN counts identical | max abs dtheta | max abs ddist | max abs daction |
|---------|----------------|---------------------|----------------|---------------|-----------------|
| +35  | 92 (92)   | 92/92   | 3.6e-15 deg | 3.6e-15 | 1.1e-16 |
| -150 | 162 (162) | 162/162 | 1.4e-14 deg | 3.6e-15 | 1.1e-16 |

- Time per window 300 / 302 ms (body 260 / 262 ms, brain + hook 40 ms); no cost from the swap.
- Remaining dependency on the reference repo: scripts still import `benchmark` (data paths) and
  `run_brian2_cuda` (default_params: w_syn, f_poi for the Poisson input weight) at module level, so the
  closed-loop scripts still need ~/refs/eon-fly-brain/code on the path. Only the network construction moved.
