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
