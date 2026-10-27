# Closed-loop fixation sweep over initial bearings (scripts/closed_loop_sweep.py)

Same loop and mapping as docs/closed-loop-v1.md (configs/brain_body_mapping.yaml), one net.run() per
15 ms window. Object at distance 20 (FlyGym units, unverified as mm), limit 2 s, stop at distance < 2,
brain seed 1, body deterministic (seed 0, 40 warm-up windows at [1,1]), one episode per bearing.
Data: docs/closed-loop-sweep.csv (theta at the start of each window, t_ms = time of that sample).
[SIMPLIFICATION]: retina/optic lobe/colour skipped; LC10 side chosen empirically; DN -> leg mapping
from the YAML.

| bearing | arrived within 2 s | arrival | first sample abs(theta) < 20 | min distance |
|---------|--------------------|---------|------------------------------|--------------|
| +25  | yes | 1260 ms | 30 ms | 2.0 |
| -25  | yes | 1380 ms | 420 ms | 2.1 |
| +50  | yes | 1440 ms | 285 ms | 2.2 |
| -50  | yes | 1830 ms | never | 2.0 |
| +90  | yes | 1710 ms | 630 ms | 2.1 |
| -90  | no  | -       | 1335 ms | 4.3 |
| +135 | no  | -       | 1035 ms | 4.7 |
| -135 | no  | -       | never | 16.4 |

Predictions made before the run: +-25, +-50, +90, +135 reach the object with abs(theta) < 20 deg within
0.3-0.9 s (negative side slower); -90 ~20 deg after 1-1.2 s; -135 fails. Outcome: -135 failure, -25 and
+90 in range, -90 slower (1.3 s) and held at about -20 deg; misses: +135 (1.04 s and no arrival in 2 s; the
115 deg turn alone needs >= 0.74 s at the maximum rate of ~155 deg/s) and -50 (arrived, but abs(theta) never
below 20 deg).

- "First sample < 20 deg" is not a convergence time: for +25 (theta(0) = 25 exactly) it is 30 ms, which with
  dtheta5 = -3.0 deg means theta is non-monotonic, most likely the yaw wobble of the stepping cycle (several
  degrees). The brain cannot act that fast (45 ms smoothing, >= 2 hops). Convergence needs a run of
  consecutive windows (see scripts/summarize_closed_loop.py).
- dtheta5 (theta change over the first 5 windows) is -1.7..-3.5 deg in all eight episodes (mean -2.75): a
  common, deterministic body transient (~40 deg/s leftwards for ~75 ms); small, but it adds to the error for
  negative bearings.
- mean_theta_after in the script output averages all windows after the first crossing (includes the
  approach), so it is not comparable with the settled errors of v1.
- Whether -90 and +135 arrive with a longer limit was not tested. n = 1 per bearing.
- Wall time 43-71 s per episode, 0.51-0.58 s per window (~0.026-0.029x real time; one net.run() per window).
