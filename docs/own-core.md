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

## Unit tests (tests/test_core_small.py; pytest, no FlyWire data, numpy target, ~1 s)

Two-neuron networks with analytic expectations (t_mbr = 20 ms, tau = 5 ms, delay 1.8 ms, w_syn = 275 uV);
tolerances were fixed before the first run. 100 synapses: peak v - v_0 = 4.33 +- 0.1 mV at 11.04 +- 0.3 ms, no
spike of neuron 1; 200 synapses: one spike of neuron 1 between 5.5 and 7.0 ms; -200 synapses: minimum
-8.66 +- 0.15 mV, no spike. load_connectome accepts consistent files and raises ValueError for an index mismatch
and for duplicate IDs. 6 passed. The Cython target is not covered by these tests (the full-network comparisons use it).

## Slow regression test (tests/test_core_full.py; pytest -m slow)

tests/data/golden_lc10_30_10.json freezes a summary of the reference implementation's spike train for the
stimulus of scripts/check_own_core.py (LC10 left 30 Hz / right 10 Hz for 0.3 s, 0.2 s silence, brain seed 1):
7322 spikes, 1122 active neurons, SHA-256 of the neuron indices and of the spike times in 0.1 ms steps, plus the
Brian2 version. Only the summary is stored (the spike train itself is derived from the connectome and its licence
for derived data was not checked). The own core reproduces it; the test took 5.3 s with a warm Cython cache
(a cold run was not timed). It detects changes in the result of this one stimulus only; a Brian2 or RNG change
can alter the hashes ("investigate", not necessarily a bug). Default `pytest` skips it (pytest.ini).

## Loop scripts without reference code (2026-10-29)

flybrain/data.py holds the data locations (env FLYBRAIN_DATA / FLYWIRE_ANN; files stay outside the repository)
and the steering-DN IDs; LIFParams.poisson_kick = w_syn * f_poi (68.75 mV; unit test added). closed_loop_sweep.py and
closed_loop_netop.py no longer import the reference repo (grep verified); the --core option was removed.
Check: closed_loop_netop.py vs docs/closed-loop-sweep-g0.82.csv: +35 deg (92 windows) and -150 deg (162 windows),
DN counts identical in all windows, actions within 1e-16, ~302 ms per window (body ~262 ms). pytest: 7 passed.

Stage 1 status: data loader with consistency check, regression tests (unit + frozen full-network summary) and the
loop on the own core are done. Not done: a swappable-engine interface (only Brian2 CPU exists; the PyTorch and GeNN
backends are deferred). Older measurement scripts (measure_dn_lateral, scan_*, map_lr_asymmetry, ...) still import
the reference code.
