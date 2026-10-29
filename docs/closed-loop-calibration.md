# Right-side gain calibration in the closed loop (scripts/closed_loop_sweep.py --gain-right)

Bearings +-35, +-70, +-110, +-150 deg, object at distance 20, 3 s limit, stop at distance < 2, brain seed 1,
one episode per bearing and per gain. gain_right 0.47 (control) vs 0.82 (= 0.47 / 0.57; 0.57 is the
DNa02_R / DNa02_L response ratio at 30 Hz from docs/lr-grid-LC10.md; a single guess, not scanned).
Data: docs/closed-loop-sweep-g0.47.csv, docs/closed-loop-sweep-g0.82.csv. [SIMPLIFICATION].

| bearing | arrival 0.47 -> 0.82 | approach error (distance 5-12) 0.47 -> 0.82 |
|---------|----------------------|---------------------------------------------|
| +35  | 1380 -> 1380 ms | +9.5 -> +9.5 deg |
| +70  | 1515 -> 1515 ms | +3.1 -> +3.1 deg |
| +110 | 1890 -> 1890 ms | +5.4 -> +5.4 deg |
| +150 | 2340 -> 2340 ms | -13.3 -> -12.0 deg |
| -35  | 1590 -> 1440 ms | -26.6 -> -13.9 deg |
| -70  | no (near miss, orbiting) -> 1650 ms | n/a -> -14.0 deg |
| -110 | 2670 -> 2010 ms | -23.5 -> -10.1 deg |
| -150 | no (distance 7.1 at 3 s) -> 2430 ms | -16.8 -> -7.7 deg |

- Convergence (5 consecutive windows with abs(theta) < 20) at 0.82 for -35/-70/-110/-150: 405/735/1050/1320 ms.
- Predictions made before the run: right approach error -5..-12 deg (observed -7.7..-14.1, 2 of 4 inside);
  right turn rate 80-120 deg/s (~86 and ~100 deg/s from convergence times, rough); -150 arrives within 3 s
  (yes); left side unchanged (yes; +150 differs slightly because DNa02_R fires sporadically there);
  no oscillation (SD of theta 4.2-5.0 deg).
- Residual asymmetry: right ~-8..-14 deg vs left +3..+9 deg. The DNa02_R/DNa02_L ratio depends on rate
  (12/34 = 0.35 at 10 Hz, 32.3/56.7 = 0.57 at 30 Hz, 73.7/84 = 0.88 at 100 Hz), and near convergence the
  LC10 rate is ~5-15 Hz, so one constant cannot equalise the two sides [analysis of the grid numbers].
- -70 at 0.47: minimum distance 2.0, 69 windows at distance 5-12, final theta -134 deg: probably a
  near miss followed by orbiting (inferred from the summary, trajectory not inspected).
- n = 1 per bearing and gain; replay results (docs/replay-open-loop.md, docs/replay-phases.csv) were
  obtained with gain_right 0.47.
