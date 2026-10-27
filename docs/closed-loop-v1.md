# First closed brain-body loop (scripts/closed_loop_fixation.py; prototype v1)

Per 15 ms window: pose -> bearing error theta of one fixed object -> Poisson rates for LC10 (left if
theta > 0, right if theta < 0; max 30 Hz, saturating at 60 deg) -> Brian2 LIF brain (one net.run() per
window) -> DNa02 spike counts -> exponential smoothing (45 ms) -> [a0, a1] (configs/brain_body_mapping.yaml)
-> 150 FlyGym steps of 0.1 ms. Object at distance 30 (FlyGym units, not verified to be mm), initial
bearings +60 and -60 deg, 3 s, one trial each, brain seed 1; the body is deterministic (seed 0, 40 warm-up
windows at [1,1]). Data: docs/closed-loop-v1.csv (theta is recorded at the start of each window,
t_ms = end of the window). [SIMPLIFICATION]: retina/optic lobe/colour skipped; LC10 side chosen
empirically (theta > 0 = positive heading change = weakening a[0]); DN -> leg mapping from the YAML.

| | object +60 deg | object -60 deg |
|---|---|---|
| first window with abs(theta) < 20 deg | 375 ms | 930 ms |
| prediction made before the run | 0.5-1 s | 1-1.5 s |
| steady state error (bins 4-14 / 7-13) | 0-3.3 deg | -14 to -19 deg |
| distance (FlyGym units) | 29.4 -> 1.1 | 29.5 -> 1.2 |

- Both runs converge towards the object with the correct sign; no oscillation or divergence.
- Forward speed ~12-13.5 units/s (not controlled by the brain; units unverified).
- Right-side steady state error is consistent with the weaker DNa02_R drive (0.2-0.4 spikes per window at
  7-9 Hz, a1 stays 0.87-0.97) plus the left-heavy bias [HYPOTHESIS, components not separated].
- After arrival (distance < ~1) the object passes under/behind the fly: theta jumps to 130-170 deg and the
  body circles; artefact of geometry and of a missing stop/approach rule. Statistics over the last 0.5 s
  (mean abs theta 146 / 145 deg) are meaningless.
- In the -60 deg run the mean theta of the first 150 ms is -65.6 deg (worse than the starting -60): possibly
  a deterministic body transient at [1,1] (~75-100 deg/s leftwards for ~100 ms), not verified.
- n = 1 per bearing; the brain seed is the only source of variability.

## Timing

Per 15 ms window: brain median 269 / 262 ms, body 296 / 276 ms; 118 s and 115 s for 3 s of behaviour
(real-time ratio ~0.025x). The brain used one net.run() per window (~170 ms fixed overhead each), not the
network_operation pattern chosen earlier (~37 ms per window measured in docs/stage0-benchmarks.md). Expected
after the change: ~330 ms per window (~0.045x), body-dominated; to be measured.
