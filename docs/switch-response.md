# Time course of the steering-DN response to a switched LC10 drive (scripts/measure_switch_response.py)

LC10 (403 L / 413 R) driven by Poisson input; protocol (rate_L, rate_R) in Hz: 0-150 ms silent,
150-450 (30,10), 450-750 (10,30), 750-1050 (30,10), 1050-1200 silent. 15 ms windows, 3 trials;
data: docs/switch-response-LC10.csv. Our simplified model [SIMPLIFICATION], not biological data.

- End-of-phase rates agree with docs/lr-grid-LC10.md: DNa02_L 1.52 / 1.62 spikes per window in the
  (30,10) phases (grid: 53 per 0.5 s = 1.6), DNa02_R 0.95 in (10,30) (grid: 25 per 0.5 s = 0.75).
- Onset from silence: DNa02_L 1.0 spike in the first 15 ms window, 1.67 in the next.
- Offset: first window after input off still 1.33 DNa02_L spikes and 67 active neurons; then 1 active
  neuron and 0 DN spikes. No persistence. Tail <= ~15 ms.
- Switch (30,10) -> (10,30): DNa02_L 1.0 in the first window, 0 afterwards; DNa02_R 0, 0, 0.67 (+30 ms),
  ~1.0 from +60 ms. Switch back: DNa02_L 1.67 at +15 ms; DNa02_R 0.33 in the first window, then 0.
  No hysteresis visible at 15 ms resolution. The +30 vs +15 ms difference is within noise; it may just
  reflect the lower rate of DNa02_R (0.95 vs 1.6 spikes per window; Poisson-detection explanation not
  tested) [HYPOTHESIS].
- DN output is 0-3 spikes per 15 ms window: a single window is too noisy for a steering command;
  smoothing over several windows is required (a design choice [SIMPLIFICATION]).
- The Brian2 warning about variable 'w' came from the loop variable of the script (renamed k_win);
  results unaffected.
