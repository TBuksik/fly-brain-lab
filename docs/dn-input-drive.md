# Where steering-DN activity comes from in the model

Script: `scripts/diagnose_dn_inputs.py`; data: `docs/dn-input-drive.csv` (5 trials, 30 Hz, 0.5 s).
Drive estimate = sum over presynaptic partners of (partner spike count x signed synapse count);
crude, ignores membrane dynamics. [SIMPLIFICATION: uniform LIF parameters, one global weight.]

## Findings (left-ORN condition, mean per trial)

- DN spike counts reproduce docs/dn-lateral-test.md (DNa02_L ~28, DNa02_R ~0.2).
- Net drive DNa02_L +8.7k vs DNa02_R -7.9k (excitatory 26.6k vs 21.1k, inhibitory 18.0k vs 29.0k);
  same pattern for right-ORN and both-sides input -> asymmetry independent of stimulus side.
  A pure threshold effect at similar drive is not supported.
- Total in-degree is nearly symmetric (DNa02: 742 vs 751 partners, 12 268 vs 13 159 synapses).
  The asymmetry sits in specific edges and upstream activity.
- Largest single contributor: AOTU019 (inhibitory in the model's sign assignment), contralateral.
  left AOTU019 -> DNa02_R: 216 synapses (~63 spikes/trial implied); right AOTU019 -> DNa02_L:
  121 synapses (~39 spikes/trial implied). MBON32 (left) -> DNa02_R: 40 synapses, inhibitory
  (~81 spikes/trial implied). Implied spike counts = contribution / weight, from rounded values.
- Cause of the left-right difference upstream is not yet known [HYPOTHESES: connectome asymmetry
  vs model artefact].
- Note: Brian2 warns that local variable `w` shadows an internal Synapses variable; harmless
  (the internal one is used).
