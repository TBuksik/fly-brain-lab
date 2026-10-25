# Lateralised drive of LC10 / PFL3 and the steering-DN response (scripts/measure_type_lateral.py)

All neurons of one cell-type family on one side driven by Poisson input (1:1 spiking), 0.5 s, 3 trials
per point; data: docs/type-lateral-LC10.csv, docs/type-lateral-PFL3.csv. Measurements of our simplified
model [SIMPLIFICATION: uniform LIF parameters, one global weight], not biological data. Driving all
LC10 of one side is NOT a visual stimulus (retina and optic lobe skipped).

## LC10 (403 left / 413 right neurons in the model), mean spikes per 0.5 s

| rate | stim left: DNa02_L / DNa02_R | stim right: DNa02_L / DNa02_R |
|------|------------------------------|-------------------------------|
| 10 Hz  | 28.0 / 0 | 0 / 11.3 |
| 30 Hz  | 57.3 / 0 | 0 / 32.0 |
| 100 Hz | 83.7 / 0 | 0 / 74.3 |

DNa01: stim left DNa01_L 0.3 / 19.0 / 16.0, stim right DNa01_R 0.3 / 11.3 / 8.0 (10 / 30 / 100 Hz).
Active neurons 490-790 (10-30 Hz), 1080-1500 (100 Hz); total spikes ~3k / ~10k / ~32-34k.

- Fully lateralised in all 18 trials (ipsilateral DN fires, contralateral silent) and graded with rate.
  No runaway cascade (compare olfaction: ~8000 active neurons, self-sustaining).
- Gain asymmetry: DNa02_L responds more strongly than DNa02_R (ratio 2.5 / 1.8 / 1.1 at 10 / 30 / 100 Hz).
- Persistence after input off not measured here.
- Consistent with Rayshubskiy et al. 2025: LC10 -> AOTU -> DNa02 mediates steering towards visual objects.

## PFL3 (12 / 12 neurons), mean spikes per 0.5 s

| rate | left PFL3 -> DNa02_R | right PFL3 -> DNa02_L |
|------|----------------------|-----------------------|
| 10 Hz  | 16.0 | 19.3 |
| 30 Hz  | 28.7 | 31.3 |
| 100 Hz | 50.0 | 59.3 |

Contralateral output, graded, near-symmetric. Direction matches the see-saw picture in the paper
(PFL3 excites the contralateral DNa02); the paper was not checked at the level of individual L/R edges.
Inhibition of the other DN cannot be seen because the model has no spontaneous activity.

## Note on the earlier ignition criterion

The script originally summarised only trials with > 1000 active neurons. That threshold was tuned to
the olfactory cascade and is meaningless for these sparse responses (LC10 at 100 Hz: ~1100 active
neurons was labelled "ignited" only marginally). The summary now averages over all trials.

## Consequence for the roadmap [HYPOTHESIS]

Vision (LC10 route) is a better first sensory channel for steering than olfaction in this model.
Colour discrimination (red vs blue) would need a different input path; LC10 are small-object
motion detectors, not colour pathways.
