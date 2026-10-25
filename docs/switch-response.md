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

## Offline analysis (scripts/analyze_switch_response.py, no new simulation)

Sign of summed DNa02 (R-L) over k windows vs the truly stronger-driven side (protocol 30 vs 10 Hz,
2 windows skipped after each switch; blocks: L 108/54/36/24/18/12, R 54/27/18/12/9/6 for k = 1/2/3/4/6/8):

| k (ms) | stronger L: correct / tie | stronger R: correct / tie |
|--------|---------------------------|---------------------------|
| 1 (15) | 0.98 / 0.02 | 0.63 / 0.37 |
| 2 (30) | 1.00 / 0.00 | 0.89 / 0.11 |
| 3 (45) | 1.00 / 0.00 | 0.94 / 0.06 |
| 4 (60) | 1.00 / 0.00 | 0.92 / 0.08 |
| 6 (90) | 1.00 / 0.00 | 1.00 / 0.00 |
| 8 (120)| 1.00 / 0.00 | 1.00 / 0.00 |

- Wrong direction: never; errors are ties (the losing DN is silent), i.e. "no turn".
- Mean summed R-L per window: -1.69 (L stronger) / +0.78 (R stronger); grows linearly with k.
- With 6-9 blocks, 100% only bounds the true rate to >~0.6-0.7 (95%, rule of three); blocks from the
  same trial are not independent; one contrast only (3:1).
- Latencies per trial: from silence first DNa02_L spike in the first window (< 15 ms) in 3/3 trials;
  after input off both DNa02 silent from +15 ms in 3/3. Switch L->R: old winner silent from +0/+15 ms,
  new winner first spike at +30/+30/+60 ms; switch R->L: new winner +15 ms in 3/3. Direction
  asymmetry consistent across 3 trials, cause not established.
- Minimum path LC10 -> DNa02 is 2 hops (1-hop path sums were zero), >= 3.6 ms of synaptic delay.
