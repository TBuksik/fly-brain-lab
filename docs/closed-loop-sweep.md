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

## Offline analysis (scripts/summarize_closed_loop.py, no simulation)

Correction: "-135 is a real failure, distance barely changed" (earlier note) was wrong. theta shrinks
monotonically (-137 deg at 150 ms -> -29 deg at 1950 ms, no wrap-around); distance grows to 24.1 (900 ms) and
falls to 16.8 (1950 ms). "Not arrived in 2 s" is a time-limit effect; arrival estimated at ~3 s (11-13 units/s
closing speed, theta staying small). -90 behaves alike (theta -25 deg, distance 4.8 at the last sample).

- Turn rate from 150 ms theta differences (error ~+-20 deg/s): left turns ~110-140 deg/s, right turns
  ~50-100 deg/s with stalls (e.g. -135: -86 -> -84 deg in 150 ms); ratio ~0.5.
- Convergence time (5 consecutive windows with abs(theta) < 20): +25 105 ms, +50 360, +90 630, +135 1110;
  none for negative bearings, a threshold artefact (settled error -16..-23 deg for -25 straddles 20 deg).
- Approach-phase error (distance 5-12, n = 31-42): +25/+50/+90/+135: +4.3/+8.2/+1.4/+2.2 deg;
  -25/-50/-90: -16.3/-31.5/-19.8 deg; SD 4.1-4.8 deg in all episodes (upper bound for the stepping-cycle yaw
  wobble). -50 shows a plateau of -28..-36 deg between 600 and 1500 ms (cause unknown, n = 1).
- Final theta at distance ~2 is meaningless (a lateral offset of 1 unit is ~30 deg); -50 ends at -71 deg.
- Fraction of windows with a DNa02 spike: left 0.21/0.39/0.41/0.52, right 0.35/0.55/0.56/0.69 for
  25/50/90/135 deg. In v1 at larger abs(theta) on the right the DNa02_R count per window was lower than
  DNa02_L (0.9/1.2/0.6/0.5 vs 1.4/1.5/0.8/0.6 in the first four 150 ms bins). Consistent with the DN
  asymmetry of docs/lr-grid-LC10.md; the stationary body curve is nearly symmetric (-75 vs +80 deg/s at
  x = 0.6). [HYPOTHESIS] the weaker right turn comes from DNa02_R output, not from the body.
- Closing speed (median distance decrease per second while abs(theta) < 30): 11.8-16.2 units/s; it
  underestimates forward speed by up to 13% (cos 30) and rests on few windows for -135. Constant forward
  speed (assumed earlier) is not supported.
