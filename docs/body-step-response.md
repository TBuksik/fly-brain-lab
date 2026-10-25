# Body step response (scripts/measure_body_step_response.py; no brain, FlyGym headless, seed 0)

Warm-up 40 windows at [1,1], then holds of 60 windows (15 ms each, 150 steps of 0.1 ms): A=[0.25,1.0],
B=[1.0,0.65], A again, C=[1,1]. Heading rate in 75 ms bins (deg/s).

| hold | mean rate from 150 ms on | last 0.3 s | prediction from docs/turning-curve.csv |
|------|--------------------------|------------|-----------------------------------------|
| A    | +150 | +148 | ~+155 (linear interpolation, a0 = 0.25) |
| B    | -69  | -50  | ~-65 (a1 = 0.65) |
| A    | +153 | +167 | ~+155 |
| C    | -8   | -34  | none (earlier [1,1] drift +4.7 deg/s over 1.5 s) |

- The body follows a step command within ~100 ms (rate crosses zero in 75-150 ms after A -> B); the
  scripted "time to 63%" (45/90/75/45 ms) is at the resolution limit (3-window smoothing).
- Steady rates match the stationary curve; no extra left-right asymmetry beyond the curve itself.
- Noise: SD of the 75 ms bins is ~23-25 deg/s (A, B) and ~40 deg/s ([1,1], range -73..+62).
  Short-window "steady" values (0.3 s) carry an error of roughly 12-20 deg/s (independence of bins
  not checked); drift estimates from windows << 1 s are unusable.
- Consequence for docs/replay-open-loop.md: body inertia is not supported as the cause of the weak
  right turn in the replay; the weaker/later DNa02_R command (and the 300 ms phase length) remains the
  candidate [HYPOTHESIS], to be tested in the closed loop.
