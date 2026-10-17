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
