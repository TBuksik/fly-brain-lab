# Global scale on recurrent weights (scripts/scan_weight_scale.py)

ORN_DA1 on one side, 20 Hz, 0.5 s on + 0.5 s off, 2 trials per point; Poisson input weight unchanged,
only syn.w scaled. Data: docs/weight-scale-scan.csv. Scaling is a tuning choice [SIMPLIFICATION].

| scale | left stim: on spikes / active / late spikes | right stim |
|-------|---------------------------------------------|------------|
| 1.0   | 214k / 8272 / 119k                          | 212k / 8315 / 119k |
| 0.8   | 144k / 6522 / 83k                           | 129k / 6499 / 83k |
| 0.6   | 22k / 2043 / 24k                            | 653 / 66 / 0 |
| <=0.5 | receptors only (580-630)                    | receptors only (654-658) |

(late = last 0.25 s of the 0.5 s without input; means of 2 trials, per-trial values in the CSV.)

- Every ignited state also persists after input off. Transition between scales 0.8 and 0.6 is sharp.
- Steering DNs respond only in the large cascade (DNa02_L 14-24 spikes, DNa02_R <= 0.5 at scales 1.0
  and 0.8; nearly silent at 0.6; silent below). No graded or side-dependent DN regime found.
- Ipsilateral effect in the DA1 ALPN readout stays small: ~27 spikes (scale 1.0), ~43 (scale 0.8),
  ~1-2% of readout activity; two trials only.
- Left stimulation ignites at a lower scale than right (0.6); one observation.
- Conclusion: scale alone does not restore a graded regime. Remaining candidates [HYPOTHESES]:
  sign assignment of synapses (excitatory/inhibitory only, same magnitude), no adaptation,
  olfaction outside the validated range of the model.
