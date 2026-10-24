# Whole-brain left-right asymmetry under lateralised olfactory input

Script: `scripts/map_lr_asymmetry.py` (30 Hz on all ORNs of one side, 0.5 s, 5 trials; spike counts
aggregated by (super_class, cell_type, side) with FlyWire v783 annotations; table not committed,
written to /tmp). [SIMPLIFICATION: uniform LIF parameters, one global weight.]

## Results ('both' condition unless stated)

- Total spikes per trial in neurons with side and cell_type annotated: left 151 205, right 132 349
  (left ~14% higher).
- 1239 of 8665 cell types have both sides and >= 20 spikes. Asymmetry index (L-R)/(L+R): median
  +0.021, mean +0.046; 57% of types left-heavy. Low-spike types are noisy, so the share with
  |AI| > 0.3 (26%) is not a reliable measure.
- Largest absolute L-R differences: Kenyon cells KCg-m (L 31 012 / R 22 731) and KCab
  (L 20 795 / R 15 543), then lLN2X12, CB2064, lLN1_bc, ORN_DC1, ORN_DL5, ...
- Lateralisation effect by super_class (ipsilateral side more active when that side is stimulated):
  sensory 0.76, central 0.01, descending -0.01. A one-sided input does not produce a one-sided
  central response; where it is lost is not yet localised.

## Open questions [HYPOTHESES]

- ORN axons project to both antennal lobes in the connectome, so "one-sided" input is split.
- Kenyon cell counts may differ between sides.
- Kenyon cell activity in the model (~90k spikes / 0.5 s) may be far denser than the sparse
  odour code reported in vivo (general literature knowledge, not checked in this project);
  relevant for stage 4 (mushroom body plasticity).

## Structural checks (scripts/check_lr_structure.py, no simulation)

- Kenyon cells in the v783 model: 2580 left vs 2597 right (KCg-m 1069 / 1120, KCab 844 / 799).
  Counts do not explain the left-heavy KC activity (KCg-m ~29 vs ~20 spikes per cell per trial,
  averaged over all cells of the type). Hypothesis "different KC counts" rejected.
- Output synapses of ORNs by target side: left ORNs 52.4% left / 47.5% right targets,
  right ORNs 51.8% / 48.1%. By target class (synapses, left ORNs): ALPN 51 752 left / 31 007 right
  (63% ipsilateral); ALLN 33 195 left / 49 177 right (40% ipsilateral). Right ORNs mirror this
  (ALPN 58% ipsilateral, ALLN 35%). So the "one-sided" stimulus is substantially bilateral at the
  first synapse; transmitter sign of the ALLN targets in the model not checked.

## Where lateralisation is lost (scripts/lateralisation_by_class.py, on the per-type table)

lat_index = ((ll - lr) - (rl - rr)) / (ll + lr + rl + rr), columns <stimulated side>_<neuron side>.

- By class: olfactory 0.712 (contra/ipsi 0.168), ALPN 0.005, ALLN 0.005, Kenyon cells 0.003,
  LHLN 0.002, DAN 0.001, MBON 0.001. Lateralisation is gone at the first relay.
- ALPN activity depends on the neuron's side, not on the stimulated side: DA1_lPN left neurons
  556 (left stim) vs 551 (right stim), right neurons 468 vs 478, while left ORN_DA1 neurons fire
  932 vs 61 in the same two conditions. DA1 projection neurons ignore a ~15-fold change in
  their cognate receptor input. Consistent with the earlier finding that total network activity
  barely depends on input strength (switch-like global state). [SIMPLIFICATION: uniform LIF
  parameters, one global weight.]
- Left-right bias is mixed in sign across types (DA1_lPN, D_adPN, VC5_lvPN left-heavy;
  DL2d_adPN, M_lPNm11D, lLN1_bc right-heavy), not a global left bias.
- ORN types differ: ORN_DA1/VA1d/VA1v contra/ipsi 0.02-0.04; ORN_VM6v 0.86, ORN_D 0.80
  (not lateralised even at receptor level; cause unknown).
- Annotation top_nt: ALLN glutamate 148, GABA 147, ACh 80, serotonin 40, dopamine 12, octopamine 2;
  ALPN ACh 474, GABA 203, glutamate 8. The sign used by the model comes from the `Excitatory`
  column of the connectivity file; not checked per class.
- Open: dense input (all ~2250 ORNs) may saturate; sparse single-glomerulus test pending.

## Sparse input: one glomerulus (scripts/measure_glomerulus_lateral.py, 100 Hz, 0.5 s, 5 trials)

Drive ORN_DA1 on one side only (60 left / 66 right neurons); readout DA1_lPN + DA1_vPN (9 left / 8 right).
Data: docs/glomerulus-lateral-ORN_DA1.csv. [SIMPLIFICATION: uniform LIF parameters, one global weight.]

- Stimulus is lateralised at the receptors (stimulated side ~2960 spikes, other side ~15-64).
- Readout L-R: +99 spikes (left stim) vs +62 (right stim), SD 1-7: small ipsilateral effect
  (~1.5% of readout activity), real but weak. Earlier "ALPN ignore the input" was too strong.
- 60 receptors give ~229k spikes and ~8300 active neurons (2250 receptors: ~257k / ~9400;
  'sugar' with 21 neurons: ~17k / ~400). Strongly saturating cascade, nearly input-independent.
- Steering DNs: DNa02_L 24-27 spikes, DNa02_R 0.2-0.6, DNa01_L ~9-11, DNa01_R ~3-4 in every
  stimulated condition, independent of stimulus side: DN output reflects the global state.
- [HYPOTHESES] cascade runs mainly through the mushroom body (dense Kenyon cell activity vs
  sparse in vivo, general literature knowledge not checked here); uniform-parameter artefact;
  Shiu et al. validation may not cover olfaction (to check in the paper).

## Dose-response, one glomerulus (ORN_DA1 one side; 3 trials per point; 0.5 s)

Data: docs/glomerulus-lateral-ORN_DA1-rate{5,10,20,50}.csv. [SIMPLIFICATION: uniform LIF
parameters, one global weight.] Per-trial ignition below is INFERRED FROM MEANS and still to be
confirmed from per-trial values.

- 5 Hz one side: only the receptors fire (~145-152 spikes); ALPN, DNs, rest of brain silent.
- 10 Hz left: means match 2 of 3 trials igniting the full cascade; 10 Hz right: 0 of 3.
  5 Hz both sides: means match 1 of 3. From 20 Hz all trials ignite.
- Ignited state: ~200-230k spikes, ~8300 active neurons, total rising only 218k (20 Hz) ->
  225k (50 Hz) -> 229k (100 Hz). DNa02_L 22-29 spikes, DNa02_R 0-0.7, DNa01_L 9-12, DNa01_R 2-4.
  DNs silent when not ignited.
- Ipsilateral effect in the ALPN readout after ignition: (L-R | left stim) - (L-R | right stim)
  ~25 spikes at 20 and 50 Hz, ~37 at 100 Hz; independent of input strength.
- Observed regimes: silent or global cascade; no graded regime seen. DN output encodes ignition
  only, not stimulus side or strength. A brain-body rule turn ~ rate(R) - rate(L) driven by
  olfactory input would give no turn or a fixed turn.
