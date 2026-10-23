# Stage 0 benchmarks (2026-10-17)

Reference model: Shiu et al. LIF whole-brain model, FlyWire v783 data, via
eonsystemspbc/fly-brain (commit a3db62f). Experiment: "sugar" (21 GRNs at 200 Hz).

## Setup
- GPU: NVIDIA RTX 4050 Laptop (6 GB), WSL2 (kernel 6.6.87.2), plugged in, performance mode
- PyTorch 2.14.1+cu126, Brian2 2.9.0, Python 3.10

## Our measurements (1 s simulated, 1 trial)
| Backend | Simulation time | Realtime ratio |
|---|---|---|
| Brian2 CPU | 2.23 s | 0.448x |
| PyTorch (CUDA) | 16.27 s | 0.061x |
| PyTorch (CUDA), batch of 4 | 67.37 s (16.8 s per trial) | 0.059x |

PyTorch uses 1.25-1.37 GB VRAM. Batching trials gives no speedup on this GPU.

## Agreement PyTorch vs Brian2 CPU (compare_ground_truth.py, 1 s)
Spikes 17,009 vs 16,776; active neurons 389 vs 411 (Jaccard 0.896);
rate correlation 0.995. Single trial each, independent Poisson noise.

## MN9 (feeding motor neuron)
Left MN9 (720575940660219265) fires in both backends (94 vs 96 spikes, first spike
30.2 vs 27.0 ms). Right MN9 (720575940645521262) is silent in both. Not yet
explained; to be checked against Shiu et al.

## Reference numbers from the Eon benchmark CSV (hardware not recorded)
Median sim time for 1 s: GeNN 0.54 s, NEST GPU 1.07 s, Brian2GeNN 1.91 s,
Brian2 CPU 2.90 s, PyTorch 9.79 s, Brian2CUDA 11.96 s.

## Labels
- [SIMPLIFICATION] all neurons share the same LIF parameters; one global weight scale.
- [HYPOTHESIS] GeNN would run near real time on this GPU; to be measured.

## GeNN attempt (2026-10-18)
- Environment: Ubuntu 26.04.1 (glibc 2.43, system gcc 15). CUDA 12.6.3 toolkit installed
  from NVIDIA's WSL-Ubuntu apt repo (cuda-compiler-12-6 + cuda-libraries-dev-12-6, about 8 GB
  on disk) with g++-13 as the nvcc host compiler.
- nvcc failed on glibc >= 2.41 (cospi/sinpi/rsqrt "exception specification is incompatible"
  in crt/math_functions.h). Workaround: added `noexcept (true)` to 6 declarations in that
  header (backup kept as math_functions.h.orig). Test kernel compiled and ran.
- PyGeNN 5.4.0 built from source with gcc-13; the GeNN model code compiled.
- Loading the model failed with CUDA out of memory (free VRAM 4.95 GiB).
- Likely cause (estimate, not verified in GeNN): the SPARSE format used by the Eon runner
  pads every row to the longest one. Max out-degree is 9,783, so about
  138,639 x 9,783 x 8 B = 10.1 GiB, against 15.1 M real connections (about 0.12 GB).
- Not tried: splitting neurons into degree classes with separate synapse groups; a larger GPU.
- Status: Brian2 CPU stays the reference and working engine.
- Open question: closed loop with the body needs control every ~15 ms; standalone Brian2
  runs the whole simulation at once. Runtime-mode speed is to be measured.

## Brian2 runtime mode, closed-loop stepping (2026-10-20)
Question: can a brain-body loop step the model every 15 ms without a huge cost?
- Repeated `net.run(window)` calls (scripts/measure_brian2_runtime.py): median wall time
  per window 0.1 ms: 170.5 ms, 1 ms: 172.2 ms, 15 ms: 215 ms (306 ms in an earlier run),
  60 ms: 322 ms, 150 ms: 610 ms. Fixed overhead of about 170 ms per `run()` call
  (cause not investigated), plus about 3 ms of wall time per simulated ms.
- One long `net.run()` with a `network_operation` hook every 15 ms
  (scripts/measure_brian2_netop.py): median 37.3 ms per window (p95 45.4 ms), realtime
  ratio 0.40x, peak RSS 2.9 GiB. Hook calls: 200 of 200. Switching the stimulus off in
  mid-run works (spikes per window: 253.8 on, 0.0 off).
- Run-to-run variation is about 30%. The hook is empty: the body step and the cost of
  reading spikes of selected neurons are not included yet.
- [SIMPLIFICATION] The model has no spontaneous activity: without input it is silent.
- [SIMPLIFICATION] Sensory input is a PoissonGroup with changeable rates instead of
  PoissonInput (same spike weight, different noise mechanism).
- Decision proposed: Brian2 runtime + network_operation as the engine for stages 2-3.

## Body (FlyGym 1.1.0) stepping, headless (2026-10-22)
scripts/measure_body_step.py: Fly with contact sensors on Tibia and Tarsus1-5 of all legs
(HybridTurningController needs Tibia/Tarsus1/Tarsus2), adhesion on, no rendering.
- 150 physics steps (0.1 ms each) per 15 ms window: median 244 ms (p95 296 ms),
  about 1.6 ms per step, realtime ratio 0.061x. Peak RSS about 0.8 GiB.
- With the brain (37 ms per window, measure_brian2_netop.py) the sum is about 281 ms per
  15 ms window (about 0.053x, 10 s of behaviour takes about 3 min). The two parts were
  measured separately, not in one loop. The body is about 87% of the time.
- Action is a 2-vector: |action[i]| sets CPG amplitude of the three legs on one side,
  the sign sets their direction. Leg movements come from CPGs and preprogrammed steps,
  not from the brain model. [SIMPLIFICATION]
- Displacement over 1.5 s (units not verified, seed 0, one run each): action [1, 1]:
  (21.1, 3.9, -0.1); action [1, 0.2]: (-2.6, -4.1, 0.0). Heading was not measured, so
  turning is not yet demonstrated.

## FlyGym body: turning response (2026-10-23)

Measured with `scripts/measure_turning_curve.py` (HybridTurningController, seed 0,
1.5 s per action, heading unwrapped, rate taken after 0.5 s). Raw data: `docs/turning-curve.csv`.

- Deterministic: repeated actions reproduce all values exactly (single seed only).
- Lowering a[1] gives negative heading change, lowering a[0] positive.
  Which side each index drives is NOT yet verified in the FlyGym source.
- For x in [0.2, 1.0] the turn rate is roughly 200 deg/s per unit of (1 - x),
  with a constant bias of about +4.7 deg/s at [1, 1].
- x = 0 behaves differently and asymmetrically (regime change, cause unknown);
  keep actions within [0.2, 1.0].
- This characterises the simulated body only; it is not biological data.

### Body action convention (verified in FlyGym source, 2026-10-23)

- Leg order (flygym/examples/locomotion/steps.py): LF, LM, LH, RF, RM, RH.
- HybridTurningController.step: a[0] sets CPG amplitude of the first three legs
  (left side), a[1] of the last three (right side). Sign of a[i] flips the stepping
  direction of that side (freqs *= -1 when a[i] <= 0).
- Measured (heading convention of obs["fly_orientation"], xy plane): weakening a[0]
  gives positive turn, weakening a[1] negative turn. World-axis handedness not checked.
- Keep brain-driven actions within [0.2, 1.0]; a == 0 flips direction (regime change).
- Each step calls get_observation twice (post_step and the controller's own call, which
  feeds the retraction/stumbling rules). Removing the second call would save at most ~17%
  of body time; deferred.
