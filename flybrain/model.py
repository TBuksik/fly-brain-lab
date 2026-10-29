"""Own implementation of the reference leaky integrate-and-fire (LIF) network.

Equations and parameters follow docs/model-parameters.md (values of the reference implementation, which follows
Shiu et al. 2024, doi:10.1038/s41586-024-07763-9). Written from that description, not copied from it.
All neurons share the same parameters and all synapses one scale [SIMPLIFICATION].
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from brian2 import NeuronGroup, SpikeMonitor, Synapses, mV, ms, uvolt

NEURON_EQS = """
dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)
dg/dt = -g / tau              : volt (unless refractory)
rfc                           : second
"""


@dataclass(frozen=True)
class LIFParams:
    """Model parameters: voltages in mV, times in ms, w_syn in uV per synapse."""
    v_0: float = -52.0
    v_rst: float = -52.0
    v_th: float = -45.0
    t_mbr: float = 20.0
    tau: float = 5.0
    t_rfc: float = 2.2
    t_dly: float = 1.8
    w_syn: float = 275.0
    f_poi: int = 250          # a Poisson input spike adds w_syn * f_poi to v

    @property
    def poisson_kick(self):
        """Voltage added to v by one Poisson input spike: w_syn * f_poi (68.75 mV)."""
        return (self.w_syn * uvolt) * self.f_poi


@dataclass
class Connectome:
    root_ids: np.ndarray          # FlyWire root IDs, position = neuron index
    pre: np.ndarray               # presynaptic neuron indices
    post: np.ndarray              # postsynaptic neuron indices
    signed_synapses: np.ndarray   # synapse count x (+1 excitatory / -1 inhibitory)

    @property
    def n_neurons(self):
        return len(self.root_ids)


@dataclass
class BrainParts:
    neurons: NeuronGroup
    synapses: Synapses
    monitor: SpikeMonitor


def load_connectome(completeness_csv, connectivity_parquet):
    """Load neuron IDs and signed connections; verify that the stored indices match the ID positions."""
    ids = pd.read_csv(completeness_csv, index_col=0).index.to_numpy(dtype=np.int64)
    if len(np.unique(ids)) != len(ids):
        raise ValueError("duplicate root IDs in the completeness file")
    con = pd.read_parquet(connectivity_parquet, columns=[
        "Presynaptic_ID", "Postsynaptic_ID", "Presynaptic_Index", "Postsynaptic_Index",
        "Excitatory x Connectivity"])
    position = pd.Series(np.arange(len(ids)), index=ids)
    for id_col, idx_col in [("Presynaptic_ID", "Presynaptic_Index"), ("Postsynaptic_ID", "Postsynaptic_Index")]:
        expected = position.reindex(con[id_col]).to_numpy()
        if not np.array_equal(expected, con[idx_col].to_numpy()):
            raise ValueError(f"{idx_col} does not match the position of {id_col} in the completeness file")
    return Connectome(root_ids=ids, pre=con["Presynaptic_Index"].to_numpy(dtype=np.int64),
                      post=con["Postsynaptic_Index"].to_numpy(dtype=np.int64),
                      signed_synapses=con["Excitatory x Connectivity"].to_numpy(dtype=np.float64))


def build_network(connectome, params=None, prefix="fb", record_spikes=True):
    """Create the Brian2 objects (neurons, synapses, spike monitor); the caller assembles the Network."""
    p = params or LIFParams()
    namespace = dict(v_0=p.v_0 * mV, v_rst=p.v_rst * mV, v_th=p.v_th * mV, t_mbr=p.t_mbr * ms, tau=p.tau * ms)
    neurons = NeuronGroup(connectome.n_neurons, model=NEURON_EQS, method="linear", threshold="v > v_th",
                          reset="v = v_rst; g = 0*mV", refractory="rfc", name=f"{prefix}_neurons",
                          namespace=namespace)
    neurons.v = p.v_0 * mV
    neurons.g = 0 * mV
    neurons.rfc = p.t_rfc * ms
    synapses = Synapses(neurons, neurons, "w : volt", on_pre="g += w", delay=p.t_dly * ms,
                        name=f"{prefix}_synapses")
    synapses.connect(i=connectome.pre, j=connectome.post)
    synapses.w = connectome.signed_synapses * (p.w_syn * uvolt)
    monitor = SpikeMonitor(neurons, name=f"{prefix}_spikes") if record_spikes else None
    return BrainParts(neurons, synapses, monitor)
