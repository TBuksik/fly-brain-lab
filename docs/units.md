# Length unit of the FlyGym body (checked 2026-10-29)

- FlyGym's fly.py documents spawn positions "in mm" (two places); no other statement about units or scaling was
  found by grep in fly.py / simulation.py.
- Measured (HybridTurningController, 400 steps at [1,1]): 72 bodies; extent of the body origins 2.90 along the
  heading, 2.98 across, 1.48 in height. The extremes are the tarsi of the hind and front legs, so this is the leg
  span, not the body length. Consistent with a millimetre-scale fly (body length ~2.5-3 mm is general knowledge, not
  checked here). Expected beforehand: ~2-3 along (met), ~1 across (missed: legs are spread).
- Therefore "FlyGym units" in earlier documents are millimetres: object distances 20-30 mm, closing speed in the
  closed loop ~12-16 mm/s (medians per bearing; docs/closed-loop-sweep.md). Not compared with the literature on
  walking speed.
- Time is in seconds (timestep 0.1 ms).
