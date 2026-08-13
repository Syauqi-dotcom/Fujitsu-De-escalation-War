import numpy as np

# MPI harus diinisialisasi sebelum Qulacs ketika proses memakai mpiQulacs.
try:
    from mpi4py import MPI as _MPI
    _comm = _MPI.COMM_WORLD
    MPI_RANK = _comm.Get_rank()
    MPI_SIZE = _comm.Get_size()
except ImportError:
    _MPI = None
    MPI_RANK = 0
    MPI_SIZE = 1

from qulacs import Observable, QuantumCircuit, QuantumState
from scipy.optimize import minimize

from src.qubo import qubo_value

HAS_NATIVE_ZZ_ROTATION = hasattr(
    QuantumCircuit, "add_multi_Pauli_rotation_gate"
)

# Qulacs lokal tetap memakai state CPU biasa; mpiQulacs mengaktifkan state
# terdistribusi hanya ketika proses memang dijalankan dalam communicator MPI.
_USE_MULTI_CPU = _MPI is not None and MPI_SIZE > 1


def _new_state(n_qubits):
    if _USE_MULTI_CPU:
        return QuantumState(n_qubits, use_multi_cpu=True)
    return QuantumState(n_qubits)


def build_observable(K, g, gamma_tf=0.0):
    m = len(g)
    obs = Observable(m)

    for k in range(m):
        if abs(g[k]) > 1e-14:
            obs.add_operator(float(g[k]), f"Z {k}")
            
    for k in range(m):
        for ell in range(k+1, m):
            if abs(K[k, ell]) > 1e-14:
                obs.add_operator(float(K[k, ell]), f"Z {k} Z {ell}")
    
    if abs(gamma_tf) > 1e-14:
        for k in range(m):
            obs.add_operator(float(-gamma_tf), f"X {k}")
    
    return obs

def build_hva_circuit(K, g, params):
    m = len(g)
    p = len(params) // 2
    gammas = params[:p]
    betas = params[p:]
    
    circuit = QuantumCircuit(m)

    for k in range(m):
        circuit.add_H_gate(k)

    for r in range(p):
        gamma=gammas[r]
        beta=betas[r]

        for k in range(m):
            angle = 2.0 * gamma * g[k]
            if abs(angle) > 1e-14:
                circuit.add_RZ_gate(k, angle)
        
        for k in range(m):
            for ell in range(k+1, m):
                angle = 2.0 * gamma * K[k, ell]
                if abs(angle) > 1e-14:
                    if HAS_NATIVE_ZZ_ROTATION:
                        circuit.add_multi_Pauli_rotation_gate(
                            [k, ell], [3, 3], angle
                        )
                    else:
                        circuit.add_CNOT_gate(k, ell)
                        circuit.add_RZ_gate(ell, angle)
                        circuit.add_CNOT_gate(k, ell)
        
        for k in range(m):
            circuit.add_RX_gate(k, 2.0 * beta)
    
    return circuit
        
def evaluate_energy_hva(params, K, g, observable, state=None):
    state = _new_state(len(g)) if state is None else state
    state.set_zero_state()
    circuit = build_hva_circuit(K, g, params)
    circuit.update_quantum_state(state)
    return observable.get_expectation_value(state).real

def build_hea_circuit(m, params, depth):
    circuit = QuantumCircuit(m)
    idx = 0 

    for k in range(m):
        circuit.add_RY_gate(k, params[idx])
        idx += 1
    
    for layer in range(depth):
        for k in range(m):
            circuit.add_RY_gate(k, params[idx])
            idx += 1
            circuit.add_RZ_gate(k, params[idx])
            idx += 1
    
        for k in range(m-1):
            circuit.add_CNOT_gate(k, k+1)
        circuit.add_CNOT_gate(m-1, 0)
    
    return circuit
    
def evaluate_energy_hea(params, m, depth, observable, state=None):
    state = _new_state(m) if state is None else state
    state.set_zero_state()
    circuit = build_hea_circuit(m, params, depth)
    circuit.update_quantum_state(state)
    return observable.get_expectation_value(state).real

def run_hva_vqe(K, g, gamma_tf=0.2, depth=2, seed=123):
    rng = np.random.default_rng(seed)
    obs = build_observable(K, g, gamma_tf=gamma_tf)

    x0 = rng.uniform(low=-0.1, high=0.1, size=2 * depth)
    energy_history = []
    state = _new_state(len(g))

    def objective(params):
        energy = evaluate_energy_hva(params, K, g, obs, state=state)
        energy_history.append(energy)
        return energy

    res = minimize(
        objective,
        x0,
        method="COBYLA",
        options={"maxiter": 300, "rhobeg": 0.5, "tol": 1e-4},
    )
    res.energy_history = energy_history
    return res 

def run_hea_vqe(K, g, gamma_tf=0.2, depth=2, seed=123):
    rng = np.random.default_rng(seed)
    m = len(g)
    obs = build_observable(K, g, gamma_tf=gamma_tf)

    # HEA parameters count: m for initial layer, then 2*m per depth layer
    num_params = m + 2 * m * depth
    x0 = rng.uniform(low=-np.pi, high=np.pi, size=num_params)
    energy_history = []
    state = _new_state(m)

    def objective(params):
        energy = evaluate_energy_hea(params, m, depth, obs, state=state)
        energy_history.append(energy)
        return energy

    res = minimize(
        objective,
        x0,
        method="COBYLA",
        options={"maxiter": 300, "rhobeg": 0.5, "tol": 1e-4},
    )
    res.energy_history = energy_history
    return res


def _decode_samples(integer_samples, n_qubits):
    encoded = np.asarray(integer_samples, dtype=np.uint64)[:, None]
    bit_positions = np.arange(n_qubits, dtype=np.uint64)[None, :]
    return ((encoded >> bit_positions) & 1).astype(np.int8)


def sample_hva_portfolios(K, g, params, n_shots=2000, seed=123):
    m = len(g)
    # §7.2: semua state remote memakai use_multi_cpu=True melalui _new_state
    # §7.4: semua rank harus memanggil sampling (jangan dibungkus if rank==0)
    state = _new_state(m)
    state.set_zero_state()
    circuit = build_hva_circuit(K, g, params)
    circuit.update_quantum_state(state)

    # §7.5: sampling harus punya seed agar reproducible
    samples = state.sampling(n_shots, seed)
    return _decode_samples(samples, m)

def sample_hea_portfolios(K, g, params, depth, n_shots=2000, seed=123):
    m = len(g)
    # §7.2: semua state remote memakai use_multi_cpu=True melalui _new_state
    # §7.4: semua rank harus memanggil sampling (jangan dibungkus if rank==0)
    state = _new_state(m)
    state.set_zero_state()
    circuit = build_hea_circuit(m, params, depth)
    circuit.update_quantum_state(state)

    # §7.5: sampling harus punya seed agar reproducible
    samples = state.sampling(n_shots, seed)
    return _decode_samples(samples, m)

def best_sampled_portfolios(samples, q, Q, const=0.0, top_k=10):
    unique = {}
    for x in samples:
        key = tuple(int(v) for v in x)
        if key not in unique:
            unique[key] = qubo_value(x, q, Q, const)
    ranked = sorted(unique.items(), key=lambda kv: kv[1])
    return ranked[:top_k]  
