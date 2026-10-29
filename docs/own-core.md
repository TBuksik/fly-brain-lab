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
