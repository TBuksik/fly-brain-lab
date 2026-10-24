# Parameters of the reference LIF model (Eon / Shiu et al. implementation), as read from code

Source: create_network and default_params in ~/refs/eon-fly-brain/code/run_brian2_cuda.py
(GPL-2.0-or-later; values noted here, code not copied). Resolves the earlier note that adaptation
and per-neuron parameters were unchecked.

- dv/dt = (v_0 - v + g) / t_mbr; dg/dt = -g / tau. v_0 = v_rst = -52 mV, v_th = -45 mV,
  t_mbr = 20 ms, tau = 5 ms, refractory 2.2 ms (per-neuron variable rfc), delay 1.8 ms.
- Spike: v = v_rst, g = 0. No adaptation, no noise, no spontaneous activity, no short-term
  plasticity. All neurons share the same parameters [SIMPLIFICATION].
- Synapse: g += w; w = (Excitatory x Connectivity) * w_syn, w_syn = 275 uV. Sign from the
  Excitatory column only (inhibition has the same scale as excitation).
- Our Poisson input (scripts/measure_*): v += w_syn * f_poi = 275 uV * 250 = 68.75 mV per input spike,
  so each input spike fires the neuron; rfc = 0 for driven neurons. Measured spike counts of driven
  neurons match rate x n x duration (e.g. 2963 vs 3000).
- Rough analysis [MODEL, not measured]: peak PSP of one synapse ~0.04 mV; mean v - v_0 =
  w_syn * n_eff * rate * tau, so threshold needs ~5100 synapse*Hz net drive (~85 net synapses from
  neurons firing at 60 Hz), ignoring fluctuations and refractoriness.
- Validation scope of Shiu et al. 2024 (Nature, doi:10.1038/s41586-024-07763-9): feeding initiation
  (sugar/water GRNs -> MN9) and antennal grooming (Johnston's organ). Olfaction was not among the
  validated circuits. Companion work: Sapkal et al. 2024 (halting in locomotion), not yet read.

## Sign assignment in the connectivity file (2025_Connectivity_783.parquet)

- Excitatory is +1/-1, one value per presynaptic neuron (no neuron has both). Synapses: ~32.49M
  excitatory (59.6%), ~22.00M inhibitory (40.4%), 54.49M total.
- By annotated top_nt (neurons +1 / -1; synapses +1 / -1): acetylcholine 84 162 / 1719 (30.19M / 0.27M);
  GABA 1348 / 17 731 (0.14M / 12.46M); glutamate 2941 / 21 863 (0.21M / 9.27M);
  dopamine 5897 / 3 (1.38M / ~0); serotonin 2127 / 9 (0.44M / ~0); octopamine 192 / 1 (0.14M / ~0).
- Neuromodulator-labelled neurons act as ordinary excitatory synapses (~3.6% of all synapses).
  5900 neurons carry top_nt = dopamine, vs 331 in cell_class DAN: top_nt is a classifier prediction
  applied to many other cell types; what those neurons are has not been checked.
- ~6000 neurons have a sign that disagrees with their top_nt label (ACh -1, GABA +1, glutamate +1);
  origin not checked.
