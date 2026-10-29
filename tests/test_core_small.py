"""Fast tests of flybrain.model on tiny synthetic networks (no FlyWire data needed).

Analytic expectations for one synaptic input of size G = n_syn * w_syn onto a neuron with t_mbr = 20 ms and
tau = 5 ms (delay 1.8 ms): v - v_0 peaks at G * tau/(t_mbr - tau) * (exp(-t*/t_mbr) - exp(-t*/tau)),
t* = t_mbr * tau / (t_mbr - tau) * ln(t_mbr / tau) = 9.24 ms after the delayed jump.
"""
import numpy as np
import pandas as pd
import pytest
from brian2 import Network, StateMonitor, mV, ms, prefs, start_scope

prefs.codegen.target = "numpy"

from flybrain.model import Connectome, LIFParams, build_network, load_connectome  # noqa: E402

P = LIFParams()


def run_two_neurons(n_syn):
    start_scope()
    con = Connectome(root_ids=np.array([11, 22], dtype=np.int64), pre=np.array([0]), post=np.array([1]),
                     signed_synapses=np.array([float(n_syn)]))
    parts = build_network(con)
    parts.neurons.v[0] = -44 * mV  # above threshold: neuron 0 spikes in the first time step
    sm = StateMonitor(parts.neurons, "v", record=1)
    net = Network(parts.neurons, parts.synapses, parts.monitor, sm)
    net.run(40 * ms)
    return parts.monitor, sm


def deflection(sm):
    t = np.asarray(sm.t / ms)
    v = np.asarray(sm.v[0] / mV) - P.v_0
    return t, v


def test_subthreshold_psp_matches_analytic_peak():
    mon, sm = run_two_neurons(100)
    t, v = deflection(sm)
    assert mon.count[0] == 1 and mon.count[1] == 0
    assert v.max() == pytest.approx(4.33, abs=0.1)          # 27.5 mV * 0.1575
    assert t[v.argmax()] == pytest.approx(1.8 + 9.24, abs=0.3)


def test_suprathreshold_input_gives_one_spike_at_the_predicted_time():
    mon, _ = run_two_neurons(200)
    assert mon.count[0] == 1 and mon.count[1] == 1
    t_spike = float(mon.t[mon.i == 1][0] / ms)
    assert 5.5 < t_spike < 7.0                              # analytic: ~6.1 ms


def test_inhibitory_input_hyperpolarises_without_spikes():
    mon, sm = run_two_neurons(-200)
    _, v = deflection(sm)
    assert mon.count[1] == 0
    assert v.min() == pytest.approx(-8.66, abs=0.15)


def write_connectome(tmp_path, ids, pre_id, post_id, pre_idx, post_idx, weight):
    comp = tmp_path / "completeness.csv"
    pd.DataFrame({"Completed": True}, index=pd.Index(ids)).to_csv(comp)
    con = tmp_path / "connectivity.parquet"
    pd.DataFrame({"Presynaptic_ID": [pre_id], "Postsynaptic_ID": [post_id], "Presynaptic_Index": [pre_idx],
                  "Postsynaptic_Index": [post_idx], "Excitatory x Connectivity": [weight]}).to_parquet(con)
    return comp, con


def test_load_connectome_accepts_consistent_files(tmp_path):
    comp, con = write_connectome(tmp_path, [11, 22, 33], 11, 22, 0, 1, -7)
    c = load_connectome(comp, con)
    assert c.n_neurons == 3
    assert c.pre.tolist() == [0] and c.post.tolist() == [1] and c.signed_synapses.tolist() == [-7.0]


def test_load_connectome_rejects_index_mismatch(tmp_path):
    comp, con = write_connectome(tmp_path, [11, 22, 33], 11, 22, 0, 2, 5)
    with pytest.raises(ValueError, match="Postsynaptic_Index"):
        load_connectome(comp, con)


def test_load_connectome_rejects_duplicate_ids(tmp_path):
    comp, con = write_connectome(tmp_path, [11, 22, 22], 11, 22, 0, 1, 5)
    with pytest.raises(ValueError, match="duplicate"):
        load_connectome(comp, con)
