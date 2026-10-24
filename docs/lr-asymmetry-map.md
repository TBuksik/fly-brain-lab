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
