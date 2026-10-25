# LC10 driven on both sides at different rates (scripts/measure_lr_grid.py)

LC10 (403 left / 413 right) driven by Poisson input at (rate_L, rate_R) in {0, 10, 30, 100}^2 Hz,
0.5 s on + 0.5 s off, 3 trials per cell; data: docs/lr-grid-LC10.csv. Measurement of our simplified
model [SIMPLIFICATION: uniform LIF parameters, one global weight]; driving LC10 is not a visual stimulus.

DNa02 R-L (mean spikes per 0.5 s); rows = rate_L, columns = rate_R (0 / 10 / 30 / 100 Hz):

|        | 0     | 10    | 30    | 100   |
|--------|-------|-------|-------|-------|
| 0      | 0.0   | 12.0  | 32.3  | 73.7  |
| 10     | -34.0 | -8.3  | 25.0  | 65.7  |
| 30     | -56.7 | -53.0 | -41.7 | 24.3  |
| 100    | -84.0 | -83.7 | -81.3 | -45.3 |

- Monotone in both inputs; Pearson r = 0.936 with (rate_R - rate_L), slope 0.846 spikes/Hz,
  intercept -15.9 (descriptive only: the data are not a function of the difference alone).
- Equal input on both sides gives R-L = 0 / -8.3 / -41.7 / -45.3 (0 / 10 / 30 / 100 Hz): a left-heavy
  bias that grows with input strength, not a constant offset. Balance point (R-L = 0): rate_R ~14 Hz
  for rate_L = 10, ~74 Hz for rate_L = 30 (linear interpolation, rough), outside the range for 100.
- Not additive: summing the one-sided responses predicts R-L ~ -17 / -25 / -9 for (10,10) / (30,30) /
  (100,100); measured -8 / -42 / -45. Mechanism unknown (needs separate DNa02_L and DNa02_R).
- DNa01 R-L: r = 0.74, slope 0.127 spikes/Hz, not monotone: not usable as a steering readout here.
- No persistence: spikes in the last 0.25 s after input off are 0 in nearly all cells (1.3 at L=0, R=100).
- Active neurons during input: 0-540 (one side) up to ~2000 (100/100).
- [HYPOTHESIS] left-heavy bias related to the contralateral inhibition by AOTU019
  (left AOTU019 -> DNa02_R: 216 synapses; right -> DNa02_L: 121; docs/dn-input-drive.md); not checked
  whether AOTU019 lies on the LC10 route.

## Competition between sides (analysis of docs/lr-grid-LC10.csv + two-hop path sums)

Separate means of DNa02_L / DNa02_R (spikes per 0.5 s), (rate_L, rate_R) in Hz:
(10,10) 12.0 / 3.7; (10,30) 0 / 25.0; (30,10) 53.0 / 0; (30,30) 43.3 / 1.7; (30,100) 25.0 / 49.3;
(100,30) 81.3 / 0; (100,100) 64.3 / 19.0. Single-side drive: DNa02_L 34 / 56.7 / 84 and DNa02_R
12 / 32.3 / 73.7 at 10 / 30 / 100 Hz; the other DN stays at 0.

- Excitation is purely ipsilateral; with both sides driven the weaker side is suppressed (often to 0):
  winner-take-all-like competition. Explains the non-additivity noted above (earlier "mechanism
  unknown" is superseded). Consistent with the see-saw picture of Rayshubskiy et al. 2025 (described
  there for PFL3 / MBON32 inputs, not for LC10).
- Two left-right asymmetries: (1) higher gain of DNa02_L at single drive (ratio 2.8 / 1.75 / 1.14);
  (2) stronger suppression of DNa02_R at equal drive (30/30: R to 5% of its single-drive value,
  L to 76%; 100/100: 26% vs 77%). At (10,10) both are suppressed to ~1/3.
- Structure (two hops, signed path sums from all LC10 of one side; 1 hop = 0, no direct synapses):
  left LC10 -> DNa02_L +1.05M, -> DNa02_R -0.59M; right LC10 -> DNa02_L -0.36M, -> DNa02_R +1.04M.
  Ipsilateral paths equal; contralateral inhibitory paths ~1.4-1.6x stronger from the left. Direction
  agrees with the measurement; crude (ignores thresholds, rates, dynamics). 3-4 hop sums are
  uninterpretable (growth ~1000x per hop, mixed signs) and unused.
- Consequence [UPROSZCZENIE needed]: R-L is not linear in (rate_R - rate_L); equal input gives a left turn
  that grows with strength. A brain-body mapping needs an explicit calibration, labelled as such.
