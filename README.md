# fly-brain-lab

A research prototype: a virtual *Drosophila melanogaster* whose behavior is meant to
emerge from a simulated nervous system built on real connectome data, not from
scripted rules. Long-term goal: a 3D environment where learning experiments
(e.g. olfactory conditioning) can be run and the resulting behavior observed.

**Status: early stage. Nothing here is a validated emulation of a fly brain.**
Currently the repository only contains the project skeleton.

## Scientific honesty

Every element of the project is labeled as one of:

- **[DATA]** - taken from real measurements (e.g. FlyWire connectome).
- **[MODEL]** - biologically justified, but requires modeling choices (e.g. a plasticity rule).
- **[SIMPLIFICATION]** - a technical shortcut (e.g. leaky integrate-and-fire neurons, hand-chosen brain-body mapping).
- **[HYPOTHESIS]** - something we still have to test.

If a behavior cannot be obtained with the current model, this repository should say so.

## Roadmap

| Stage | Goal |
|---|---|
| 0 | Reproduce the published whole-brain LIF model (Shiu et al.) and measure speed on a laptop GPU |
| 1 | Own core library: data loading, LIF engine with swappable backend, regression tests |
| 2 | Closed loop with a simulated body (FlyGym), headless |
| 3 | Sensory input: olfaction, then vision |
| 4 | Plasticity in the mushroom body and associative learning experiments |
| 5 | Experiment panel, saving and loading state, before/after comparison |
| 6 | 3D environment and neuron activity visualization |

## Layout

- `src/flybrain/` - library code
- `configs/` - experiment and brain-body mapping configs
- `scripts/` - data download and experiment runners
- `tests/` - regression tests against reference results
- `docs/` - notes and design decisions
- `data/`, `results/` - not tracked by git

## Building on

- Dorkenwald et al., *Neuronal wiring diagram of an adult brain*, Nature 2024. doi:10.1038/s41586-024-07558-y
- Shiu et al., *A Drosophila computational brain model reveals sensorimotor processing*, Nature 2024. doi:10.1038/s41586-024-07763-9
- Wang-Chen et al., *NeuroMechFly v2*, Nature Methods 2024. doi:10.1038/s41592-024-02497-y
- Lappalainen et al., *Connectome-constrained networks predict neural activity across the fly visual system*, Nature 2024. doi:10.1038/s41586-024-07939-3
- Vaxenburg et al., *Whole-body physics simulation of fruit fly locomotion*, Nature 2025. doi:10.1038/s41586-025-09029-4

## License

To be decided.
