# Open-loop replay: recorded steering-DN counts -> body (scripts/replay_dn_on_body.py)

Recorded per-window DNa02 spike counts (docs/switch-response-LC10.csv, 3 trials) are mapped to FlyGym
actions with configs/brain_body_mapping.yaml and stepped in the headless HybridTurningController
(150 steps of 0.1 ms per 15 ms window, 10 warm-up windows at [1,1]); the brain is not running.
Data: docs/replay-phases.csv. The mapping is an explicit [SIMPLIFICATION] (a_side = clip(1 - 0.47 x
smoothed DNa02 spikes per window of that side, 0.2, 1), smoothing tau 45 ms). A first version of the
script treated radians as degrees; its results were discarded (never committed).

| phase (rate_L, rate_R) | mean action in 2nd half | heading change | rate, whole phase | rate, 2nd half |
|------------------------|-------------------------|----------------|-------------------|----------------|
| (30,10) [150-450 ms]   | [0.24, 1.00] | +25.2 deg | +84 deg/s | +130 deg/s |
| (10,30) [450-750 ms]   | [0.99, 0.65] | +9.3 deg  | +31 deg/s | -18 deg/s  |
| (30,10) [750-1050 ms]  | [0.25, 1.00] | +23.0 deg | +77 deg/s | +124 deg/s |
| no input [1050-1200]   | [0.92, 1.00] | +10.3 deg | +69 deg/s | +22 deg/s  |

(means of 3 trials; spread across trials 10-30% in the (30,10) rates.)

- Left-turn command works: 2nd-half rate ~80% of the stationary prediction (+156 deg/s for a0 = 0.24,
  interpolated from docs/turning-curve.csv).
- Right-turn command barely turns the body: 2nd-half rate -18 deg/s vs ~-65 deg/s predicted for a1 = 0.65
  (~28%); the whole phase still has positive heading change. The body keeps turning left for a while,
  also after the input is switched off.
- Rates from windows shorter than ~300 ms are unreliable (stepping cycle; phase 0 shows -30 deg/s in the
  2nd half with zero input).
- Possible contributions, not separated [HYPOTHESES]: weaker DNa02_R activity (right command strength
  1 - a1 = 0.35 vs 0.76 for the left, ratio ~0.46); body inertia/lag when reversing the turn; smoothing
  and the late first spikes of DNa02_R (+30-60 ms).
