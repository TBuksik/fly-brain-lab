# Separate scales for excitatory and inhibitory weights (scripts/scan_ei_balance.py)

ORN_DA1 on one side, 20 Hz, 0.5 s on + 0.5 s off, 3 trials per point; Poisson input weight unchanged.
Data: docs/ei-balance-scan.csv. Multipliers are tuning choices [SIMPLIFICATION].

- All 48 trials ignited the cascade (> 1000 active neurons), so ignition is not the limiting factor.
- Cascade size (active neurons, left stimulation) falls with inhibition: exc 1.0: 8293 (inh 1.0),
  5004 (1.5), 3344 (2.0), 2252 (3.0); exc 0.8: 4860 (1.0), 2760 (1.5), 2218 (2.0), 1601 (3.0).
- Persistence in every condition: late rate (last 0.25 s after input off) = 1.08-1.10 x the rate
  during input.
- DNa02_L spikes (left stimulation): 24.0 (exc 1.0 / inh 1.0), 9.0, 1.3, 1.0 for inh 1.0 / 1.5 / 2.0 / 3.0;
  DNa02_R ~0 throughout. DNs fall silent together with the cascade; no regime in which DN output
  depends on stimulus side.
- Lateralisation index of the DA1 ALPN readout rises as the cascade shrinks: 1.4% (1.0/1.0),
  1.9% (inh 1.5), 2.5% (2.0), 4.9% (3.0); at exc 0.8: 3.2%, 4.8%, 4.6%, ~16% (inh 3.0, 3 trials,
  one side reversed: not reliable).
- Conclusion: the olfactory route does not carry stimulus side or strength to the steering DNs in any
  tested regime; olfaction lies outside the validated range of the model (Shiu et al. 2024).
