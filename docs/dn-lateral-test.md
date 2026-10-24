# Lateral olfactory input vs steering DN activity (Brian2 CPU, Shiu LIF, FlyWire v783)

Script: `scripts/measure_dn_lateral.py`. Data: `docs/dn-lateral-test.csv` (100 Hz, 3 trials),
`docs/dn-lateral-test-rate30.csv` (30 Hz, 10 trials). 0.5 s per trial, all ORNs of one side
(annotation soma side; 1116 left, 1133 right) driven by Poisson input, DNa01/DNa02 spike counts
(IDs: docs/descending-neurons.md). These are measurements of our simplified model
[SIMPLIFICATION: uniform LIF parameters, one global weight], not biological data.

## Results (mean spikes per 0.5 s trial)

| condition (30 Hz) | DNa01_L | DNa01_R | DNa02_L | DNa02_R |
|-------------------|---------|---------|---------|---------|
| none              | 0.0     | 0.0     | 0.0     | 0.0     |
| left ORNs         | 10.6    | 3.8     | 25.8    | 0.5     |
| right ORNs        | 9.1     | 3.4     | 26.6    | 0.2     |
| both              | 10.6    | 5.1     | 27.8    | 0.6     |

At 100 Hz the picture is the same (DNa02_L 30.7 / 26.3 / 28.3 for left / right / both).

## Findings

- No input -> no spikes (no spontaneous activity in the model).
- No detectable lateralisation: left vs right stimulation differ by less than the trial-to-trial
  spread (SD ~2-3 spikes).
- Large, condition-independent asymmetry: DNa02_L fires ~26 spikes, DNa02_R ~0.4; DNa01_L ~10,
  DNa01_R ~4. Cause unknown [HYPOTHESES: real connectome asymmetry / model artefact / ORN
  projections are bilateral].
- The network response barely depends on input strength: 3.3x lower rate gave ~19% fewer total
  spikes; doubling the number of stimulated ORNs (both sides) gave ~10% more. Rates below
  30 Hz were not tested.
- Consequence: a brain-body rule turn ~ rate(R) - rate(L) driven by this input would give a constant
  turn direction. The model as it stands does not reproduce the lateralised DNa02 response
  reported in vivo (Rayshubskiy et al. 2025).
